# -*- coding: utf-8 -*-

import os
import sys
from PIL import Image, ImageDraw

directory = os.path.dirname(os.path.abspath(__file__))

DEFAULT_INPUT_FILE = os.path.join(directory, 'init01.csv')                     #имя констант всегда заглавными буквами
OUTPUT_FILE_CSV = os.path.join(directory,'generation.csv')
OUTPUT_FILE_PNG = os.path.join(directory,'generation.png')

DEFAULT_GENERATIONS = 10                                                        #константа генерации
DEBUG = False

CELL_SIZE = 20
BORDER_WIDTH = 2

LIVE_COLOR = (0, 255, 0)

def live_neighbors(grid, row, col):
    '''
    Подсчитывает количество живых соседей клетки.

    Живой считается клетка, значение которой больше 0
    (значение интерпретируется как возраст клетки).

    @requires:
        grid — прямоугольный двумерный список списков целых чисел,
        где 0 — мёртвая клетка, значение > 0 — живая клетка.
        row, col — корректные индексы клетки.
    @modifies: None
    @effects: None
    @returns:
        целое число — количество живых соседей клетки
    '''  

    count = 0
    rows = len(grid)
    cols = len(grid[0])
    if row >= 1:
        min_r = row - 1
    else:
        min_r = 0
    max_r = row + 1 if row < rows - 1 else row
    min_c = col - 1 if col >= 1 else 0
    max_c = col + 1 if col < cols - 1 else col
#    print(f'{row} {col}')
    for idx_y in range(min_r, max_r + 1):
        for idx_x in range(min_c, max_c + 1):
            #print(f'The value of grid [{idx_x}][{idx_y}] is {grid[idx_y][idx_y]}')
            if idx_y == row and idx_x == col:
                continue
            if grid[idx_y][idx_x] > 0:
                count += 1
    return count

def model(grid):

    # Написать спецификаии для всех остальных функций и потом пишем тесты
    '''
    Формирует следующее поколение игрового поля
    для игры «Жизнь» на основе текущего состояния.

    Каждая клетка представлена целым числом:
    - 0 — мёртвая клетка
    - положительное целое — живая клетка, значение
      соответствует её возрасту.

    Правила перехода:
        1. Живая клетка с количеством живых соседей < 2 умирает.
        2. Живая клетка с 2 или 3 живыми соседями выживает,
           и её возраст увеличивается на 1.
        3. Живая клетка с количеством живых соседей > 3 умирает.
        4. Мёртвая клетка с ровно 3 живыми соседями оживает
           и получает возраст 1.

    :param grid: двумерный список (список списков),
                 содержащий 0 или положительные целые числа
    :return: новое двумерное игровое поле следующего поколения

    Функция не изменяет исходное поле grid.
    '''

    rows, cols = len(grid), len(grid[0])
    new_grid = [[0 for _ in range(cols)] for _ in range(rows)]      # _ используется для элемента который нужно указать, но он не используется
#    print(new_grid)
    for row in range(rows):
        for col in range(cols):
            live_nb = live_neighbors(grid, row, col)

            if grid[row][col] > 0:
                if live_nb < 2 or live_nb > 3:
                    new_grid[row][col] = 0
                else:
                    new_grid[row][col] = grid[row][col] + 1
            else:
                if live_nb == 3:
                    new_grid[row][col] = 1
    return new_grid

def read_input(filename):
    '''
    Считывает входной CSV-файл и формирует начальное игровое поле.

    Формат файла:
        0 — мёртвая клетка
        1 — живая клетка

    Значения в строке разделяются символом ';'.

    @param filename: путь к входному файлу
    @return:
        grid — двумерный список целых чисел
    @raises:
        FileNotFoundError — если файл не найден
        ValueError — если формат файла некорректен
    '''

    grid =[]
    with open(filename, "r") as input_file:
        lines = input_file.readlines()
        #print(f'File contents: {lines}')
        for line in lines:
            line = line.strip()
            line = line.split(';')
            line = [int(elem) for elem in line]
            grid.append(line)
    return grid

def write_output(grid, filename):
#    pass
    '''
    Записывает игровое поле в CSV-файл.

    @param grid: двумерный список игрового поля
    @param filename: имя выходного CSV-файла
    @return: None
    '''

    with open(filename, 'w') as f:
        for row in grid:
            f.write(';'.join(str(cell) for cell in row) + '\n')

# запись на картинку пока не делать.
def write_png(grid, filename):

    """
    Необходимо создать PNG-изображение игрового поля для игры «Жизнь».

    Игровое поле представляется в виде двумерного списка, где:
    >0 — живая клетка с возрастом (отображается закрашенной),
    0 — мёртвая клетка (отображается пустой).

    Изображение сохраняется в формате PNG.

    :param grid: двумерный список (список списков) одинаковой длины, содержащий значения 0 и >0
    :param filename: имя выходного PNG-файла (строка)
    :return: None
    :raises ValueError: если grid имеет некорректную структуру
    :raises IOError: если файл не удалось сохранить
    """

    rows, cols = len(grid), len(grid[0])

    width = cols * (CELL_SIZE + BORDER_WIDTH) + BORDER_WIDTH
    height = rows * (CELL_SIZE + BORDER_WIDTH) + BORDER_WIDTH
    
    # cols = 4 CELL_SIZE = 10 BORDER_WIDTH = 2
    # 4 * 12 = 48
    # ||          ||          ||          ||          ||
    
    im = Image.new("RGB", (width, height), (0, 0, 0))
    #im.show()
    draw = ImageDraw.Draw(im)

    for row in range(rows):
        for col in range(cols):
            if grid[row][col] > 0:
                x1 = BORDER_WIDTH + col * (CELL_SIZE + BORDER_WIDTH)
                y1 = BORDER_WIDTH + row * (CELL_SIZE + BORDER_WIDTH)
                x2 = x1 + CELL_SIZE
                y2 = y1 + CELL_SIZE

                draw.rectangle(
                    [(x1, y1), (x2, y2)],
                    fill=LIVE_COLOR
                )
    im.save(filename)

input_file = DEFAULT_INPUT_FILE
generations = DEFAULT_GENERATIONS
# input_file = input('Enter input file name: ')
# print(sys.argv)
# sys.exit()
if len(sys.argv) > 1:
    param_name, param_value = sys.argv[1].split('=')
    if param_name == 'initfile':
        input_file = param_value
if len(sys.argv) > 2:
    param_name, param_value = sys.argv[2].split('=')
    if param_name == 'gen':
        generations = int(param_value)

try:
    grid = read_input(input_file)
except OSError:
    print(f'Cannot open file {input_file}, falling back to the default file name of {DEFAULT_INPUT_FILE}.')
    input_file = DEFAULT_INPUT_FILE
    grid = read_input(input_file)

'''
for gen in range(GENERATIONS):
    grid = model(grid)
    write_output(grid, OUTPUT_FILE_CSV)
    write_png(grid, OUTPUT_FILE_PNG)
'''

if DEBUG:
    expected = \
          [ [0, 0, 0],
            [1, 1, 0],
            [0, 0, 0],
          ]
    actual = model(grid)
    write_output(actual, OUTPUT_FILE_CSV)
    if actual != expected:
        print('Test model failed!')

    expected = 3
    actual = live_neighbors(grid, 1, 0)
    if actual != expected:
        print('Test 1 live_neighbors failed!')

    expected = 1
    actual = live_neighbors(grid, 2, 2)
    if actual != expected:
        print('Test 2 live_neighbors failed!')

    corner_test_grid = [
    [1, 1, 0],
    [1, 0, 0],
    [0, 0, 0]
    ]
    expected = 2  # верхний левый угол имеет 2 живых соседа
    actual = live_neighbors(corner_test_grid, 0, 0)
    if actual != expected:
        print('Corner cell live_neighbors test failed!')
    else:
        print('Corner cell live_neighbors test passed!')
    
    write_png(grid, OUTPUT_FILE_PNG)

    expected = 0
    actual = live_neighbors(grid, 0, 1)
    if actual != expected:
        print('Test 3 live_neighbors failed!')
    
    write_png(grid, OUTPUT_FILE_PNG)

    print('All tests passed')

else:
    for gen in range(generations):
        grid = model(grid)

        write_output(
            grid,
            os.path.join(directory, f'generation_{gen}.csv')
        )

        write_png(
            grid,
            os.path.join(directory, f'generation_{gen}.png')
        )
