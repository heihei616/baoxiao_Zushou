"""中文大写金额转换（人民币，纯标准库）。

示例：
    1327.50 -> 壹仟叁佰贰拾柒圆伍角整
    10080.00 -> 壹万零捌拾圆整
"""


def num_to_cn_capital(amount):
    if amount is None:
        return ""
    try:
        amount = round(float(amount) + 1e-9, 2)
    except (TypeError, ValueError):
        return ""
    if amount < 0:
        return "负" + num_to_cn_capital(-amount)

    integer_part = int(amount)
    decimal_part = round(int(round(amount - integer_part, 2) * 100))

    if integer_part == 0 and decimal_part == 0:
        return "零圆整"

    digits = "零壹贰叁肆伍陆柒捌玖"
    int_units = ["", "拾", "佰", "仟"]
    big_units = ["", "万", "亿", "万亿"]

    def _int_to_cn(num):
        if num == 0:
            return ""
        result = ""
        for i in range(len(big_units)):
            section = num % 10000
            if section != 0:
                section_str = ""
                zero_flag = False
                for j in range(4):
                    d = section % 10
                    section //= 10
                    if d != 0:
                        if zero_flag:
                            section_str = digits[0] + section_str
                            zero_flag = False
                        section_str = digits[d] + int_units[j] + section_str
                    elif not zero_flag and section_str != "":
                        zero_flag = True
                section_str = section_str.lstrip(digits[0])
                if section_str == "":
                    section_str = digits[0]
                result = section_str + big_units[i] + result
            num //= 10000
        result = result.replace(digits[0] + digits[0], digits[0]).strip(digits[0])
        return result if result else digits[0]

    def _dec_to_cn(cents):
        jiao = cents // 10
        fen = cents % 10
        if jiao == 0 and fen == 0:
            return "整"
        out = ""
        if jiao != 0:
            out += digits[jiao] + "角"
        if fen != 0:
            if jiao == 0:
                out += digits[0]
            out += digits[fen] + "分"
        return out

    int_cn = _int_to_cn(integer_part)
    dec_cn = _dec_to_cn(decimal_part)
    if integer_part == 0:
        return dec_cn
    if dec_cn == "整":
        return int_cn + "圆整"
    return int_cn + "圆" + dec_cn


if __name__ == "__main__":
    for v in [1327.50, 10080.00, 0.50, 0, 1234567.89]:
        print(v, "->", num_to_cn_capital(v))
