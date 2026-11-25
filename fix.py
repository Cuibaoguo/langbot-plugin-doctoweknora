import re
p = r"components\runner\doc_to_weknora.py"
s = open(p, encoding="utf-8").read()

# 1. 删 _cleanup 调用
s = s.replace("        self._cleanup(file_seg)\n", "")

# 2. 删 _cleanup 方法定义（@staticmethod 到 pass + 空行）
s = re.sub(
    r"    @staticmethod\n    def _cleanup\(file_seg\):\n(?:.*\n)*?            pass\n\n",
    "",
    s,
)

# 3. 删 _download 开头的诊断日志（# 诊断 到 warning 那行 + 空行）
s = re.sub(
    r"        # 诊断：打印文件段所有非空字段\n(?:.*\n)*?        logging\.getLogger\(__name__\)\.warning\(f\"\[DocToWeKnora\] file_seg 字段: \{preview\}\"\)\n\n",
    "",
    s,
)

open(p, "w", encoding="utf-8", newline="\n").write(s)
print("done")
