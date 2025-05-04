#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

DANGEROUS_COMMANDS = {'flush', 'reset_db', 'migrate'}

def confirm_dangerous_operation(command):
    """危险操作二次确认"""
    from django.core.management.base import CommandError
    confirm = input(f"⚠️ 即将执行危险命令 [{command}]，确认继续？(yes/no): ")
    if confirm.lower() != 'yes':
        raise CommandError("操作已取消")

def main():
    """Run administrative tasks."""
    # 危险命令拦截
    if len(sys.argv) >= 2 and sys.argv[1] in DANGEROUS_COMMANDS:
        confirm_dangerous_operation(sys.argv[1])

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'KGRS.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()