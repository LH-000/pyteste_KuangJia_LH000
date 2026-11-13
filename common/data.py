# -*- coding: utf-8 -*-
"""faker 测试数据工厂：生成唯一的用户分组名。"""
import random

from faker import Faker

fa = Faker("zh_CN")

# 前缀用于肉眼区分手工/自动数据，也用于兜底清理时识别本框架残留
PREFIX = "自动化"


def group_name() -> str:
    """生成唯一分组名：自动化_<色名><4位数字>，长度控制在表单限制内。"""
    return f"{PREFIX}_{fa.color_name()}_{random.randint(1000, 9999)}"
