import time
from recommender.recommendations.graph_based import (
    RuleBasedPathFinder, TransEPathFinder
)


def benchmark(finder_class):
    start = time.time()
    finder = finder_class()
    metrics = {'time': 0, 'length': 0, 'prereq_satisfied': 0}

    # 测试用例：用户A到课程X的路径
    path = finder.find_path('user_123', 'course_AI101')

    metrics['time'] = time.time() - start
    metrics['length'] = len(path)
    metrics['prereq_satisfied'] = check_prerequisites(path)
    return metrics


def compare_methods():
    print("| 方法 | 耗时(s) | 路径长度 | 先修满足率 |")
    print("|------|---------|----------|------------|")

    # 测试规则方法
    rule_metrics = benchmark(RuleBasedPathFinder)
    print(
        f"| 规则 | {rule_metrics['time']:.2f} | {rule_metrics['length']} | {rule_metrics['prereq_satisfied'] * 100}% |")

    # 测试TransE方法
    transE_metrics = benchmark(TransEPathFinder)
    print(
        f"| TransE | {transE_metrics['time']:.2f} | {transE_metrics['length']} | {transE_metrics['prereq_satisfied'] * 100}% |")


def check_prerequisites(path):
    # 实现先修条件检查逻辑
    return 1.0  # 示例返回值