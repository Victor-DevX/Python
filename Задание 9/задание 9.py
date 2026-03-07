"""
Логика последовательности Фибоначи
F0 = 0
F1 = 1
Fn = Fn-1 + Fn-2
"""

class Fibo:
    def __init__(self):
        """
        @requires: Ничего
        @modifies: Атрибуты экземпляра класса prev и curr
        @effects: Инициализирует начальное состояние последовательности Фибоначчи (0 и 1)
        @raises: Ничего
        @returns: Ничего
        """
        self.prev = 0
        self.curr = 1
        self.index = 0

    def __iter__(self):
        """
        @requires: Экземпляр класса Fibo должен быть создан
        @modifies: Ничего
        @effects: Возвращает сам объект, который будет использоваться как итератор
        @raises: Ничего
        @returns: Итератор последовательности Фибоначчи
        """
        return self

    def __next__(self):
        """
        @requires: Экземпляр класса Fibo должен быть инициализирован
        @modifies: Атрибуты prev и curr объекта
        @effects: Вычисляет следующее число последовательности Фибоначчи
        @raises: Ничего
        @returns: Следующее число последовательности Фибоначчи
        """
        if self.index == 0:
            self.index += 1
            return 0
        elif self.index == 1:
            self.index += 1
            return 1
        else:
            next_value = self.prev + self.curr
            self.prev, self.curr = self.curr, next_value
            self.index += 1
            return self.curr


"""
Генератор integers
бесконечный счётчик
"""

def integers():
    """
    @requires: Ничего
    @modifies: Локальную переменную счетчика генератора
    @effects: Генерирует бесконечную последовательность неотрицательных целых чисел начиная с 0
    @raises: Ничего
    @returns: Следующее неотрицательное целое число
    """
    n = 0
    while True:
        yield n
        n += 1


"""
Генератор primes

Условия для каждого числа:
- если число > 1

- проверить делимость от 2 до √n, 
если делаитель >√n, то есть парный <√n

"""

def primes():
    """
    @requires: Ничего
    @modifies: Локальные переменные генератора
    @effects: Генерирует бесконечную последовательность простых чисел
    @raises: Ничего
    @returns: Следующее простое число
    """
    n = 2
    while True:
        is_prime = True
        divisor = 2
        while divisor * divisor <= n:
            if n % divisor == 0:
                is_prime = False
                break
            divisor += 1
        if is_prime:
            yield n
        n += 1

