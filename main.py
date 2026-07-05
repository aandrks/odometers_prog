import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar
import io

from streamlit_gsheets import GSheetsConnection

# ------------------------------------------------------------
# 1. Загрузка конфигурации из секретов (car_numbers + cars)
# ------------------------------------------------------------
def load_config():
    """
    Загружает из st.secrets:
      - car_numbers: словарь {номер_авто: телефон}
      - cars_list: список номеров автомобилей для контроля
    """
    try:
        car_numbers = dict(st.secrets["car_numbers"])
        cars_list = list(st.secrets["cars"]["list"])
        return car_numbers, cars_list
    except (AttributeError, KeyError, TypeError):
        st.error("❌ Не найдены секретные данные. "
                 "Убедитесь, что в secrets.toml есть секции [car_numbers] и [cars].")
        st.stop()

# ------------------------------------------------------------
# 2. Основная логика (НЕ ИЗМЕНЕНА, только добавлен параметр cars_list)
# ------------------------------------------------------------
def get_odometers(df_od, dt_date, car_numbers, cars_list):
    """
    Возвращает:
      - result_dict: {car_number: разница пробега}
      - log_no_data_cars: список строк с предупреждениями
      - log_values: список проблемных записей
      - d1_cars, d2_cars: списки машин, по которым есть данные в каждом периоде
      - difference_current, difference_last: списки отсутствующих
    """
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
            continue

        if d1 < t < d2:
            try:
                dict1[row['car_number']] = row['odometer']
            except Exception:
                log.append(row)
        elif d3 < t < d4:
            dict2[row['car_number']] = row['odometer']

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

    # Используем переданный список cars_list вместо жёстко заданного
    difference_current = [c for c in cars_list if c not in d1_cars]
    difference_last = [c for c in cars_list if c not in d2_cars]

    log_no_data_cars = []
    log_no_data_cars.append(f"Нет данных за период {d1.strftime('%d.%m.%Y')} - {d2.strftime('%d.%m.%Y')}: {difference_current}")
    log_no_data_cars.append(f"Нет данных за период {d3.strftime('%d.%m.%Y')} - {d4.strftime('%d.%m.%Y')}: {difference_last}")

    return result_dict, log_no_data_cars, log_values_local, d1_cars, d2_cars, difference_current, difference_last

# ------------------------------------------------------------
# 3. Инициализация сессии
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
    if 'car_numbers' not in st.session_state or 'cars_list' not in st.session_state:
        car_numbers, cars_list = load_config()
        st.session_state.car_numbers = car_numbers
        st.session_state.cars_list = cars_list

# ------------------------------------------------------------
# 4. Функция загрузки данных из Google Sheets
# ------------------------------------------------------------
@st.cache_data(ttl=600)
def load_data_from_gsheet():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read()
        return df
    except Exception as e:
        st.error(f"❌ Ошибка при загрузке данных из Google Sheets: {e}")
        return None

# ------------------------------------------------------------
# 5. Streamlit UI
# ------------------------------------------------------------
def main():
    st.set_page_config(page_title="Анализ пробега", layout="wide")
    st.title("📊 Анализ пробега автомобилей")

    init_session()

    menu = st.sidebar.radio(
        "Навигация",
        ["Загрузка данных", "Обработка", "Результаты", "Справка"]
    )

    # ---------- Загрузка данных ----------
    if menu == "Загрузка данных":
        st.header("📂 Загрузка данных из Google Sheets")

        col1, col2 = st.columns(2)
        with col1:
            year = st.selectbox("Год", list(range(2020, 2030)), index=datetime.now().year - 2020)
        with col2:
            month = st.selectbox("Месяц", list(range(1, 13)), index=datetime.now().month - 1)

        last_day = calendar.monthrange(year, month)[1]
        dt_date = datetime(year, month, last_day)
        st.write(f"Выбрана дата: **{dt_date.strftime('%d.%m.%Y')}**")

        if st.button("Сохранить дату"):
            st.session_state.dt_date = dt_date
            st.success("Дата сохранена!")

        st.divider()

        if st.button("📥 Загрузить данные из Google Sheets"):
            with st.spinner("Загрузка данных из Google Sheets..."):
                df = load_data_from_gsheet()
                if df is not None:
                    required_cols = ['Timestamp', 'Гос. номер автомобиля (только 3 цифры)', 'Текущий пробег (значение на одометре) (только число)']
                    if all(col in df.columns for col in required_cols):
                        st.session_state.df_od = df
                        st.success(f"✅ Данные успешно загружены! Получено {len(df)} записей.")
                        st.dataframe(df.head(10))
                    else:
                        st.error(f"❌ Таблица должна содержать колонки: {', '.join(required_cols)}")
                        st.write("Найденные колонки:", list(df.columns))
                df = df.rename(columns={
                    'Timestamp': 'time',
                    'Гос. номер автомобиля (только 3 цифры)': 'car_number',
                    'Текущий пробег (значение на одометре) (только число)': 'odometer'
                })

        st.divider()
        st.subheader("Текущее состояние сессии")
        st.write("Дата:", st.session_state.dt_date)
        if st.session_state.df_od is not None:
            st.write(f"Данные загружены: ✅ ({len(st.session_state.df_od)} записей)")
        else:
            st.write("Данные загружены: ❌")

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
                    cars_list = st.session_state.cars_list

                    result_dict, logs, log_vals, d1_cars, d2_cars, diff_cur, diff_last = get_odometers(
                        df, dt, car_numbers, cars_list
                    )

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
            df_res = pd.DataFrame(list(res['result_dict'].items()), columns=['Автомобиль', 'Разница пробега'])
            df_res = df_res.sort_values('Автомобиль')
            st.subheader("Разница пробега (текущий месяц – предыдущий)")
            st.dataframe(df_res, use_container_width=True)

            st.subheader("📋 Логи")
            for log_msg in res['logs']:
                st.text(log_msg)

            with st.expander("Подробные списки машин"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Машины с данными в текущем периоде:**", res['d1_cars'])
                    st.write("**Машины без данных в текущем периоде:**", res['diff_cur'])
                with col2:
                    st.write("**Машины с данными в предыдущем периоде:**", res['d2_cars'])
                    st.write("**Машины без данных в предыдущем периоде:**", res['diff_last'])

            st.subheader("💾 Скачать результаты")
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_res.to_excel(writer, sheet_name='Разница', index=False)
                log_df = pd.DataFrame(res['logs'], columns=['Сообщение'])
                log_df.to_excel(writer, sheet_name='Логи', index=False)
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
           - Выберите месяц и год.  
           - Нажмите «Загрузить данные из Google Sheets».  
           - Таблица должна содержать колонки: `time`, `car_number`, `odometer`.  
           - Формат времени: `день/месяц/год часы:минуты:секунды`.  
           - Нажмите «Сохранить дату».

        2. **Обработка** – нажмите «Выполнить расчёт».

        3. **Результаты** – просмотр и скачивание Excel-отчёта.

        **Примечания:**  
        - Данные из Google Sheets кешируются на 10 минут.  
        - Справочники `car_numbers` и `cars` загружаются из защищённых секретов Streamlit.
        """)

if __name__ == "__main__":
    main()