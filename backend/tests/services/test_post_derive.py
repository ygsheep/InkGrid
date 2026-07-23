"""文章派生字段自动生成测试。"""
from app.services.post_derive import (
    calculate_reading_time,
    derive_slug,
    generate_excerpt,
    generate_toc,
)


class TestGenerateExcerpt:
    def test_simple_paragraph(self):
        md = "# 标题\n\n这是第一段正文内容。"
        assert generate_excerpt(md) == "这是第一段正文内容。"

    def test_skip_headings(self):
        md = "# 大标题\n## 小标题\n\n正文段落。"
        assert generate_excerpt(md) == "正文段落。"

    def test_strip_markdown(self):
        md = "**粗体**和*斜体*以及`代码`和[链接](http://x.com)。"
        result = generate_excerpt(md)
        assert "**" not in result
        assert "*" not in result
        assert "`" not in result
        assert "[]" not in result
        assert "链接" in result

    def test_strip_image(self):
        md = "![alt text](http://x.com/img.png)\n\n后面的文字。"
        assert generate_excerpt(md) == "后面的文字。"

    def test_truncate_long_text(self):
        long_text = "a" * 300
        md = f"# T\n\n{long_text}"
        result = generate_excerpt(md)
        assert len(result) <= 200
        assert result.endswith("…")

    def test_empty_content(self):
        assert generate_excerpt("") == ""

    def test_only_headings(self):
        assert generate_excerpt("# 标题\n## 副标题") == ""

    def test_multiline_paragraph(self):
        md = "# 标题\n\n第一行\n第二行\n\n第二段。"
        result = generate_excerpt(md)
        assert "第一行" in result
        assert "第二行" in result
        assert "第二段" not in result


class TestCalculateReadingTime:
    def test_empty(self):
        assert calculate_reading_time("") == 1

    def test_chinese(self):
        md = "中" * 800  # 800 字 / 400 cpm = 2 分钟
        assert calculate_reading_time(md) == 2

    def test_english(self):
        md = " ".join(["word"] * 440)  # 440 词 / 220 wpm = 2 分钟
        assert calculate_reading_time(md) == 2

    def test_mixed(self):
        md = "中" * 400 + " " + " ".join(["word"] * 220)
        # 400/400 + 220/220 = 1 + 1 = 2
        assert calculate_reading_time(md) == 2

    def test_code_block_ignored(self):
        md = "```\n" + "x" * 1000 + "\n```\n\n短文本"
        assert calculate_reading_time(md) == 1

    def test_minimum_one(self):
        assert calculate_reading_time("短") == 1


class TestGenerateToc:
    def test_basic(self):
        md = "# H1\n## H2\n### H3"
        toc = generate_toc(md)
        assert len(toc) == 3
        assert toc[0]["level"] == 1
        assert toc[0]["title"] == "H1"
        assert toc[1]["level"] == 2
        assert toc[2]["level"] == 3

    def test_empty(self):
        assert generate_toc("") == []

    def test_no_headings(self):
        assert generate_toc("正文没有标题。") == []


class TestDeriveSlug:
    def test_english(self):
        assert derive_slug("Hello World") == "hello-world"

    def test_chinese_preserved(self):
        # slugify 保留中文
        slug = derive_slug("架构设计")
        assert "架构设计" in slug

    def test_empty_title(self):
        assert derive_slug("") == "untitled"
