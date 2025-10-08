from calc_m1 import calculate_expression

def main():
    expression = input("Введите выражение: ")
    try:
        result = calculate_expression(expression)
        print("Результат:", result)
    except Exception as e:
        print("Ошибка:", e)

if __name__ == "__main__":
    main()
