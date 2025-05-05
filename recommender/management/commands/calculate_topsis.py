# recommender/management/commands/calculate_topsis.py
from django.core.management.base import BaseCommand
import numpy as np
import pandas as pd
from django.db import transaction
from recommender.models import Concept


class Command(BaseCommand):
    help = '计算概念的熵权TOPSIS评分（极端数据优化版）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='批量更新数量（默认1000）'
        )
        parser.add_argument(
            '--smooth-factor',
            type=float,
            default=0.1,
            help='零值替换系数（默认0.1）'
        )

    def handle(self, *args, **options):
        self.stdout.write("开始计算熵权TOPSIS评分...")

        try:
            # ================= 数据获取阶段 =================
            queryset = Concept.objects.all().values('id', 'depth', 'dependency_count')
            df = pd.DataFrame.from_records(queryset)

            if df.empty:
                self.stdout.write(self.style.WARNING("没有找到概念数据"))
                return

            # ================= 数据预处理阶段 =================
            matrix = df[['depth', 'dependency_count']].values.astype(float)
            total_records = len(df)

            # 添加高斯噪声防止全零（幅度为1e-12）
            matrix += np.random.normal(0, 1e-12, matrix.shape)

            # 处理depth指标（负向指标）
            depth_col = matrix[:, 0]
            non_zero_depth = depth_col[depth_col > 0]
            depth_replace = non_zero_depth.mean() * 0.1 if len(non_zero_depth) > 0 else 1.0
            matrix[:, 0] = 1 / np.where(depth_col == 0, depth_replace, depth_col)

            # 处理dependency_count指标（极端偏态分布优化）
            dep_col = matrix[:, 1]
            non_zero_dep = dep_col[dep_col > 0]
            non_zero_count = len(non_zero_dep)

            # 当非零占比<1%时的特殊处理
            if non_zero_count / total_records < 0.01:
                self.stdout.write(f"检测到极端偏态分布（非零占比：{non_zero_count / total_records:.2%}），启用优化方案")

                # 应用拉普拉斯平滑
                dep_col += 1
                self.stdout.write("✅ 已应用拉普拉斯平滑 (+1)")

                # 零值替换为最小非零值的比例
                min_non_zero = non_zero_dep.min() if non_zero_count > 0 else 1.0
                dep_col = np.where(
                    dep_col == 0,
                    min_non_zero * options['smooth_factor'],
                    dep_col
                )
                self.stdout.write(f"✅ 零值替换为最小非零值的{options['smooth_factor'] * 100}%")

                matrix[:, 1] = dep_col

            # ================= 标准化阶段 =================
            norm_matrix = matrix / (np.sqrt(np.sum(matrix ** 2, axis=0)) + 1e-12)

            # ================= 熵权计算阶段 =================
            # 概率矩阵（限制在[1e-12, 1]区间）
            p = norm_matrix / (np.sum(norm_matrix, axis=0) + 1e-12)
            p = np.clip(p, 1e-12, 1.0)

            # 熵值计算（处理极端情况）
            entropy = -np.sum(p * np.log(p), axis=0) / np.log(len(df))
            entropy = np.nan_to_num(entropy, nan=1.0)  # 处理可能的NaN
            entropy = np.clip(entropy, 0.0, 0.9999)  # 确保1-entropy > 0

            # 权重计算（动态调整）
            weights = (1 - entropy) / (np.sum(1 - entropy) + 1e-12)

            # 对低占比指标进行权重衰减
            if non_zero_count / total_records < 0.01:
                weights[1] *= 0.3  # 被依赖次数权重衰减到30%
                weights /= np.sum(weights)  # 重新归一化
                self.stdout.write(f"⚠️ 被依赖次数权重衰减至：{weights[1]:.2%}")

            # ================= TOPSIS计算阶段 =================
            weighted_matrix = norm_matrix * weights
            pos_ideal = np.nanmax(weighted_matrix, axis=0)
            neg_ideal = np.nanmin(weighted_matrix, axis=0)

            d_pos = np.sqrt(np.nansum((weighted_matrix - pos_ideal) ** 2, axis=1))
            d_neg = np.sqrt(np.nansum((weighted_matrix - neg_ideal) ** 2, axis=1))
            topsis_scores = d_neg / (d_pos + d_neg + 1e-12)

            # ================= 数据更新阶段 =================
            batch_size = options['batch_size']
            concepts = []
            for idx, row in df.iterrows():
                # 数值安全处理
                entropy_val = np.clip(weights[0], 0.0, 1.0)
                topsis_val = np.clip(topsis_scores[idx], 0.0, 1.0)

                concepts.append(
                    Concept(
                        id=row['id'],
                        entropy_weight=entropy_val,
                        topsis_score=topsis_val
                    )
                )

            with transaction.atomic():
                Concept.objects.bulk_update(
                    concepts,
                    ['entropy_weight', 'topsis_score'],
                    batch_size=batch_size
                )

            # ================= 结果报告阶段 =================
            self.stdout.write(self.style.SUCCESS(
                "✅ 计算完成\n"
                f"总记录数: {total_records}\n"
                f"非零被依赖次数记录: {non_zero_count} ({non_zero_count / total_records:.2%})\n"
                f"最终权重分布 => 深度权重: {weights[0]:.4f}, 被依赖次数权重: {weights[1]:.4f}\n"
                f"TOPSIS评分范围: [{np.nanmin(topsis_scores):.4f}, {np.nanmax(topsis_scores):.4f}]"
            ))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ 计算失败：{str(e)}"))
            # 调试信息输出
            if 'matrix' in locals():
                self.stderr.write(f"矩阵样本（前5行）：\n{matrix[:5]}")
            if 'weights' in locals():
                self.stderr.write(f"权重值：{weights}")
            raise e