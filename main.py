import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import calendar
import io

# ------------------------------------------------------------
# 1. Загрузка справочника car_numbers (из JSON или встроенного)
# ------------------------------------------------------------
def load_car_numbers():
    try:
        with open("car_numbers.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        # Если файл отсутствует, используем встроенный словарь
        return {
            "333": "+79859277555",
            "497": "+79857210030",
            "709": "+79265504676",
            "121": "+79939038347",
            "057": "+79104104470",
            "970": "+79163772309",
            "428": "+79153777817",
            "614": "+79853905512",
            "274": "+79895734460",
            "664": "+79852720605",
            "647": "+79258265909",
            "945": "+79067686376",
            "830": "+79067686376",
            "586": "+79152374830",
            "072": "+79266943423",
            "774": "+79852720605",
            "311": "+79163669920",
            "020": "+79168245466",
            "273": "+79163849416",
            "252": "+79152645414",
            "977": "+79166431453",
            "930": "+79262497028",
            "587": "+79042912992",
            "358": "+79852720605",
            "582": "+79162178390",
            "913": "+79166431873",
            "697": "+79152402457",
            "633": "+79192536801",
            "558": "+79263209045",
            "947": "+79104676609",
            "265": "+79104676609",
            "380": "+79163770929",
            "934": "+79857777094",
            "213": "+79163665325",
            "862": "+79161997942",
            "923": "",
            "895": "",
            "295": "+79163772309",
            "253": "+79199997488",
            "970": "+79151003309"
        }

# ------------------------------------------------------------
# 2. Основная логика (скопирована из Colab без изменений)
# ------------------------------------------------------------
def get_odometers(df_od, dt_date, car_numbers):
    """
    Возвращает:
      - result_dict: {car_number: разница пробега}
      - log_no_data_cars: список строк с предупреждениями
      - log_values: список проблемных записей
      - d1_cars, d2_cars: списки машин, по которым есть данные в каждом периоде
      - difference_current, difference_last: списки отсутствующих
    """
    # Список контролируемых машин (оставлен как в оригинале)
    cars = [
        '709', '664', '647', '945', '830', '586', '072', '774', '311', '020',
        '273', '252', '977', '930', '587', '358', '582', '913', '697', '633',
        '333', '558', '947', '380', '121', '934', '213', '862', '497', '057',
        '970', '428', '614', '923', '895'
    ]

    dict1 = {}
    dict2 = {}
    log = []
    log_values_local = []

    d1 = dt_date - timedelta(days=10)
    d2 = dt_date + timedelta(days=15)
    d3 = dt_date - timedelta(days=40)
    d4 = dt_date - timedelta(days=14)

    for _, row in df_od.iterrows():
        try:
            t = pd.to_datetime(row['time'], format="%d/%m/%Y %H:%M:%S")
        except Exception:
            continue  # пропускаем некорректные даты

        if d1 < t < d2:
            try:
                dict1[row['car_number']] = row['odometer']
            except Exception:
                log.append(row)
        elif d3 < t < d4:
            dict2[row['car_number']] = row['odometer']

    # Очистка и преобразование в int
    dict1_result = {}
    dict2_result = {}
    d1_cars = []
    d2_cars = []

    for k, v in dict1.items():
        k = k.strip()
        try:
            dict1_result[k] = int(v)
            d1_cars.append(k)
        except (ValueError, TypeError):
            log_values_local.append([k, v, "2"])

    for k, v in dict2.items():
        k = k.strip()
        try:
            dict2_result[k] = int(v)
            d2_cars.append(k)
        except (ValueError, TypeError):
            log_values_local.append([k, v, "1"])

    common_keys = set(dict1_result) & set(dict2_result)
    result_dict = {k: int(dict1_result[k]) - int(dict2_result[k]) for k in common_keys}

    # Машины, по которым нет данных в каждом периоде
    difference_current = [c for c in cars if c not in d1_cars]
    difference_last = [c for c in cars if c not in d2_cars]

    log_no_data_cars = []
    log_no_data_cars.append(f"Нет данных за период {d1.strftime('%d.%m.%Y')} - {d2.strftime('%d.%m.%Y')}: {difference_current}")
    log_no_data_cars.append(f"Нет данных за период {d3.strftime('%d.%m.%Y')} - {d4.strftime('%d.%m.%Y')}: {difference_last}")

    # Дополнительно сохраняем все логи в одну строку (для вывода)
    return result_dict, log_no_data_cars, log_values_local, d1_cars, d2_cars, difference_current, difference_last

# ------------------------------------------------------------
# 3. Инициализация состояния сессии
# ------------------------------------------------------------
def init_session():
    if 'df_od' not in st.session_state:
        st.session_state.df_od = None
    if 'dt_date' not in st.session_state:
        st.session_state.dt_date = None
    if 'results' not in st.session_state:
        st.session_state.results = None
    if 'logs' not in st.session_state:
        st.session_state.logs = None
    if 'car_numbers' not in st.session_state:
        st.session_state.car_numbers = load_car_numbers()

# ------------------------------------------------------------
# 4. Streamlit UI
# ------------------------------------------------------------
def main():
    st.set_page_config(page_title="Анализ пробега", layout="wide")
    st.title("📊 Анализ пробега автомобилей")

    init_session()

    # Боковое меню
    menu = st.sidebar.radio(
        "Навигация",
        ["Загрузка данных", "Обработка", "Результаты", "Справка"]
    )

    # ---------- Загрузка данных ----------
    if menu == "Загрузка данных":
        st.header("📂 Загрузка данных и выбор даты")

        # Выбор месяца и года
        col1, col2 = st.columns(2)
        with col1:
            year = st.selectbox("Год", list(range(2020, 2030)), index=datetime.now().year - 2020)
        with col2:
            month = st.selectbox("Месяц", list(range(1, 13)), index=datetime.now().month - 1)

        # Вычисляем последний день месяца
        last_day = calendar.monthrange(year, month)[1]
        dt_date = datetime(year, month, last_day)
        st.write(f"Выбрана дата: **{dt_date.strftime('%d.%m.%Y')}**")

        if st.button("Сохранить дату"):
            st.session_state.dt_date = dt_date
            st.success("Дата сохранена!")

        st.divider()

        # Загрузка файла
        uploaded_file = st.file_uploader(
            "Загрузите файл с данными пробега (CSV или Excel)",
            type=["csv", "xlsx", "xls"]
        )

        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file, engine='openpyxl')

                # Проверка наличия нужных колонок
                required_cols = ['time', 'car_number', 'odometer']
                if all(col in df.columns for col in required_cols):
                    st.success("Файл загружен успешно!")
                    st.dataframe(df.head(10))
                    if st.button("Сохранить данные в сессию"):
                        st.session_state.df_od = df
                        st.success("Данные сохранены для обработки!")
                else:
                    st.error(f"Файл должен содержать колонки: {', '.join(required_cols)}")
                    st.write("Найденные колонки:", list(df.columns))
            except Exception as e:
                st.error(f"Ошибка при чтении файла: {e}")

        # Показать текущее состояние
        st.divider()
        st.subheader("Текущее состояние сессии")
        st.write("Дата:", st.session_state.dt_date)
        st.write("Данные загружены:", st.session_state.df_od is not None)

    # ---------- Обработка ----------
    elif menu == "Обработка":
        st.header("⚙️ Запуск расчёта")

        if st.session_state.df_od is None:
            st.warning("Сначала загрузите данные на вкладке 'Загрузка данных'.")
        elif st.session_state.dt_date is None:
            st.warning("Сначала выберите и сохраните дату на вкладке 'Загрузка данных'.")
        else:
            if st.button("▶️ Выполнить расчёт"):
                with st.spinner("Идёт обработка..."):
                    df = st.session_state.df_od
                    dt = st.session_state.dt_date
                    car_numbers = st.session_state.car_numbers

                    result_dict, logs, log_vals, d1_cars, d2_cars, diff_cur, diff_last = get_odometers(
                        df, dt, car_numbers
                    )

                    # Сохраняем в сессию
                    st.session_state.results = {
                        'result_dict': result_dict,
                        'd1_cars': d1_cars,
                        'd2_cars': d2_cars,
                        'diff_cur': diff_cur,
                        'diff_last': diff_last,
                        'log_vals': log_vals,
                        'logs': logs
                    }
                    st.success("Расчёт завершён! Перейдите на вкладку 'Результаты'.")

        # Если результаты уже есть, показываем краткую информацию
        if st.session_state.results:
            st.subheader("Результаты предыдущего расчёта")
            res = st.session_state.results
            st.write(f"Найдено машин с данными за оба периода: **{len(res['result_dict'])}**")
            st.write("Логов:", len(res['logs']))

    # ---------- Результаты ----------
    elif menu == "Результаты":
        st.header("📈 Результаты обработки")

        res = st.session_state.results
        if res is None:
            st.info("Расчёт ещё не выполнен. Перейдите на вкладку 'Обработка'.")
        else:
            # Таблица с разницей пробега
            df_res = pd.DataFrame(list(res['result_dict'].items()), columns=['Автомобиль', 'Разница пробега'])
            df_res = df_res.sort_values('Автомобиль')
            st.subheader("Разница пробега (текущий месяц – предыдущий)")
            st.dataframe(df_res, use_container_width=True)

            # Логи по отсутствующим данным
            st.subheader("📋 Логи")
            for log_msg in res['logs']:
                st.text(log_msg)

            # Дополнительная информация
            with st.expander("Подробные списки машин"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Машины с данными в текущем периоде:**", res['d1_cars'])
                    st.write("**Машины без данных в текущем периоде:**", res['diff_cur'])
                with col2:
                    st.write("**Машины с данными в предыдущем периоде:**", res['d2_cars'])
                    st.write("**Машины без данных в предыдущем периоде:**", res['diff_last'])

            # Скачивание результатов
            st.subheader("💾 Скачать результаты")
            # Формируем Excel-файл в памяти
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_res.to_excel(writer, sheet_name='Разница', index=False)
                # Логи
                log_df = pd.DataFrame(res['logs'], columns=['Сообщение'])
                log_df.to_excel(writer, sheet_name='Логи', index=False)
                # Списки
                detail_df = pd.DataFrame({
                    'Период': ['Текущий', 'Предыдущий'],
                    'Машины с данными': [', '.join(res['d1_cars']), ', '.join(res['d2_cars'])],
                    'Машины без данных': [', '.join(res['diff_cur']), ', '.join(res['diff_last'])]
                })
                detail_df.to_excel(writer, sheet_name='Сводка', index=False)
            output.seek(0)

            st.download_button(
                label="📥 Скачать Excel-отчёт",
                data=output,
                file_name=f"результаты_пробег_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    # ---------- Справка ----------
    else:
        st.header("📖 Справка")
        st.markdown("""
        **Как пользоваться приложением:**

        1. **Загрузка данных**  
           - Выберите месяц и год, за который нужно проанализировать пробег.  
           - Загрузите файл с данными (CSV или Excel).  
           - Файл должен содержать колонки: `time`, `car_number`, `odometer`.  
           - Формат времени: `день/месяц/год часы:минуты:секунды` (например, `15/03/2025 10:30:00`).  
           - Нажмите «Сохранить дату» и «Сохранить данные в сессию».

        2. **Обработка**  
           - На вкладке «Обработка» нажмите кнопку «Выполнить расчёт».  
           - Расчёт использует логику из оригинального Colab-блокнота.

        3. **Результаты**  
           - Просмотрите таблицу с разницей пробега.  
           - Ознакомьтесь с логами – там перечислены автомобили, по которым нет данных.  
           - Скачайте полный отчёт в Excel.

        **Примечания:**  
        - Все временные файлы не сохраняются на диск – данные хранятся только в памяти сессии.  
        - Справочник `car_numbers` загружается из файла `car_numbers.json` (если есть) или используется встроенный.
        """)

if __name__ == "__main__":
    main()