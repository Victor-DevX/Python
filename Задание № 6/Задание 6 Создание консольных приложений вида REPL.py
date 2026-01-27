import os        # создание относительного пути
import math
import zip_util  # модуль от преподавателя

# Заменить рабочую директорию на папку, где лежит скрипт
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Поиск по индексу
def find_zip(zip_codes, zip_code):
    '''
    Находит запись с данными по указанному почтовому индексу.
    @requires:
        zip_codes — список списков с данными о почтовых индексах США,
        zip_code — строка, представляющая почтовый индекс.
    @modifies: None
    @effects: None
    @returns:
        список с данными о почтовом индексе, если он найден,
        либо None, если индекс отсутствует в наборе данных
    '''
    for item in zip_codes:
        if item[0] == zip_code:
            return item
    return None

# поиск по критериям
def find_city_state(zip_codes, city, state):
    '''
    Находит все почтовые индексы для заданного города и штата.
    Поиск не чувствителен к регистру символов.
    @requires:
        zip_codes — список списков с данными о почтовых индексах США,
        city — строка с названием города,
        state — строка с названием штата.
    @modifies: None
    @effects: None
    @returns:
        список строк — почтовых индексов, соответствующих городу и штату;
        пустой список, если совпадений не найдено
    '''
    result = []
    for item in zip_codes:
        if item[3].lower() == city.lower() and item[4].lower() == state.lower():
            result.append(item[0])
    return result

# преобразование координат
def to_dms(value, is_latitude=True):
    '''
    Преобразует координату, заданную в градусах, в формат DMS
    (градусы, минуты, секунды) с указанием стороны света.
    @requires:
        value — вещественное число, представляющее координату в градусах,
        is_latitude — логическое значение:
            True для широты, False для долготы.
    @modifies: None
    @effects: None
    @returns:
        строка с координатой в формате DMS
        (например: 042∘40'25.32"N)
    '''
    direction = ''
    if is_latitude:
        direction = 'N' if value >= 0 else 'S'
    else:
        direction = 'E' if value >= 0 else 'W'

    value = abs(value)
    degrees = int(value)
    minutes_float = (value - degrees) * 60
    minutes = int(minutes_float)
    seconds = (minutes_float - minutes) * 60

    return f"{degrees:03d}∘{minutes:02d}'{seconds:05.2f}\"{direction}"

# расчёт расстояния между точками
def haversine(lat1, lon1, lat2, lon2):
    '''
    Вычисляет геодезическое расстояние между двумя точками на поверхности Земли
    с использованием формулы гаверсинусов. Расстояние выводится в милях.
    @requires:
        lat1, lon1 — широта и долгота первой точки (float, в градусах),
        lat2, lon2 — широта и долгота второй точки (float, в градусах).
    @modifies: None
    @effects: None
    @returns:
        вещественное число — расстояние между точками в милях
    '''
    R = 3958.8  # интернет - радиус Земли в милях
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))

# код-основа
def main():
    '''
    Реализует консольное приложение в режиме REPL для работы
    с данными о почтовых индексах США.
    Поддерживаемые команды:
        loc  — поиск местоположения по ZIP-коду,
        zip  — поиск ZIP-кодов по городу и штату,
        dist — вычисление расстояния между двумя ZIP-кодами,
        end  — завершение работы программы.
    @requires:
        наличие файла с данными о ZIP-кодах,
        корректная работа функции zip_util.read_zip_all().
    @modifies: None
    @effects:
        взаимодействие с пользователем через консоль,
        вывод информации и сообщений об ошибках.
    @returns:
        None
    '''

    zip_codes = zip_util.read_zip_all()

    if not zip_codes:
        print("Program terminated due to missing data file")
        return

    commands = {'loc', 'zip', 'dist', 'end'}

    while True:
        cmd = input("Command ('loc', 'zip', 'dist', 'end') => ").strip().lower()

        if cmd not in commands:
            print("Invalid command, ignoring")
            continue

        if cmd == 'end':
            print("Done")
            break

        elif cmd == 'loc':
            zip_code = input("Enter a ZIP Code to lookup => ").strip()
            print(zip_code)
            data = find_zip(zip_codes, zip_code)
            if not data:
                print("Error: ZIP Code not found")
                continue
            lat_dms = to_dms(data[1], True)
            lon_dms = to_dms(data[2], False)
            print(f"ZIP Code {zip_code} is in {data[3]}, {data[4]}, {data[5]} county,")
            print(f"coordinates: ({lat_dms},{lon_dms})")

        elif cmd == 'zip':
            city = input("Enter a city name to lookup => ").strip()
            print(city)
            state = input("Enter the state name to lookup => ").strip()
            print(state)
            zips = find_city_state(zip_codes, city, state)
            if not zips:
                print("Error: City or state not found")
                continue
            print(f"The following ZIP Code(s) found for {city.title()}, {state.upper()}: " + ", ".join(sorted(zips)))

        elif cmd == 'dist':
            zip1 = input("Enter the first ZIP Code => ").strip()
            print(zip1)
            zip2 = input("Enter the second ZIP Code => ").strip()
            print(zip2)
            z1 = find_zip(zip_codes, zip1)
            z2 = find_zip(zip_codes, zip2)
            if not z1 or not z2:
                print("Error: One or both ZIP Codes not found")
                continue
            dist = haversine(z1[1], z1[2], z2[1], z2[2])
            print(f"The distance between {zip1} and {zip2} is {dist:.2f} miles")

if __name__ == "__main__":
    main()
