#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动生成 README.md 目录（TOC）

功能：
1. 扫描仓库中所有 Markdown 文件（忽略 .git/, scripts/, images/）
2. 按分类目录编号排序（01-, 02-, ...）
3. 生成 Markdown 链接格式的目录
4. 只替换 README.md 中 <!-- TOC START --> 和 <!-- TOC END --> 之间的内容
5. 不修改 README.md 其他内容

用法：
    python3 scripts/generate_toc.py
"""

import os
import re
import sys

# 仓库根目录（脚本所在目录的上一级）
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# README.md 路径
README_PATH = os.path.join(REPO_ROOT, "README.md")

# TOC 标记
TOC_START = "<!-- TOC START -->"
TOC_END = "<!-- TOC END -->"

# 忽略的目录
IGNORE_DIRS = {".git", "scripts", "images", ".github"}

# 忽略的文件
IGNORE_FILES = {"README.md"}


def scan_markdown_files(repo_root):
    """
    扫描仓库中所有 Markdown 文件，按分类目录组织。

    返回：
        dict: {分类目录名: [文件路径, ...]}
    """
    categories = {}

    for root, dirs, files in os.walk(repo_root):
        # 过滤忽略的目录
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        # 计算相对于仓库根目录的路径
        rel_root = os.path.relpath(root, repo_root)

        # 跳过根目录（根目录下的 md 文件不加入目录）
        if rel_root == ".":
            continue

        # 获取分类目录名（第一级目录）
        parts = rel_root.split(os.sep)
        category = parts[0]

        # 扫描 Markdown 文件
        for filename in files:
            if not filename.endswith(".md"):
                continue
            if filename in IGNORE_FILES:
                continue

            # 相对于仓库根目录的文件路径
            file_path = os.path.join(rel_root, filename)
            # 统一使用正斜杠
            file_path = file_path.replace(os.sep, "/")

            if category not in categories:
                categories[category] = []
            categories[category].append(file_path)

    return categories


def get_title_from_file(file_path):
    """
    从 Markdown 文件中提取标题（第一个 # 开头的行）。
    如果没有找到标题，使用文件名（去掉 .md 后缀）。
    """
    full_path = os.path.join(REPO_ROOT, file_path)
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # 匹配 # 标题（支持 #, ##, ### 等）
                match = re.match(r"^#+\s*(.+?)\s*$", line)
                if match:
                    return match.group(1)
    except Exception as e:
        print(f"警告：读取文件 {file_path} 失败: {e}", file=sys.stderr)

    # 如果没有找到标题，使用文件名
    filename = os.path.basename(file_path)
    return filename[:-3] if filename.endswith(".md") else filename


def generate_toc(categories):
    """
    根据分类和文件列表生成 TOC 内容。

    格式：
        ### 03-驱动开发基础
        - [linux ioctl操作](./03-驱动开发基础/linux-ioctl操作.md)
        - [input子系统](./03-驱动开发基础/input子系统.md)
    """
    lines = []

    # 按分类目录名排序（01-, 02-, ...）
    sorted_categories = sorted(categories.keys())

    for category in sorted_categories:
        files = categories[category]
        # 按文件名排序
        files.sort()

        # 分类标题
        lines.append(f"### {category}")
        lines.append("")

        # 文件列表
        for file_path in files:
            title = get_title_from_file(file_path)
            # 生成 Markdown 链接，路径以 ./ 开头
            link_path = f"./{file_path}"
            lines.append(f"- [{title}]({link_path})")

        lines.append("")

    # 去掉末尾多余的空行
    while lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)


def update_readme_toc(readme_path, toc_content):
    """
    更新 README.md 中的 TOC 区域。
    只替换 <!-- TOC START --> 和 <!-- TOC END --> 之间的内容。
    如果标记不存在，返回 False。
    """
    try:
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"错误：读取 README.md 失败: {e}", file=sys.stderr)
        return False

    # 检查 TOC 标记是否存在
    if TOC_START not in content or TOC_END not in content:
        print(f"错误：README.md 中未找到 {TOC_START} 或 {TOC_END} 标记", file=sys.stderr)
        return False

    # 构建新的 TOC 区域（包含标记）
    new_toc_block = f"{TOC_START}\n{toc_content}\n{TOC_END}"

    # 使用正则替换 TOC 区域（非贪婪匹配）
    pattern = re.escape(TOC_START) + r".*?" + re.escape(TOC_END)
    new_content = re.sub(pattern, new_toc_block, content, flags=re.DOTALL)

    # 检查内容是否有变化
    if new_content == content:
        print("TOC 无需更新（内容未变化）")
        return False

    # 写入新内容
    try:
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("README.md TOC 已更新")
        return True
    except Exception as e:
        print(f"错误：写入 README.md 失败: {e}", file=sys.stderr)
        return False


def main():
    """主函数"""
    print(f"仓库根目录: {REPO_ROOT}")
    print(f"README.md: {README_PATH}")
    print()

    # 1. 扫描 Markdown 文件
    print("正在扫描 Markdown 文件...")
    categories = scan_markdown_files(REPO_ROOT)
    total_files = sum(len(files) for files in categories.values())
    print(f"找到 {len(categories)} 个分类，共 {total_files} 个 Markdown 文件")
    print()

    # 2. 生成 TOC
    print("正在生成目录...")
    toc_content = generate_toc(categories)
    print()

    # 3. 更新 README.md
    print("正在更新 README.md...")
    updated = update_readme_toc(README_PATH, toc_content)

    if updated:
        print()
        print("完成！README.md 目录已更新。")
        sys.exit(0)
    else:
        print()
        print("完成。目录无需更新。")
        sys.exit(0)


if __name__ == "__main__":
    main()
