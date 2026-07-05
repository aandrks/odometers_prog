import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar
import io

from streamlit_gsheets import GSheetsConnection

# ------------------------------------------------------------
# 1. Загрузка конфигурации из секретов
# ------------------------------------------------------------
def load_config():
    try:
        car_numbers = dict(st.secrets["car_numbers"])
        cars_list = list(st.secrets["cars"])
        return car_numbers, cars_list
    except (AttributeError, KeyError, TypeError):
        st.error("❌ Не найдены секретные данные. "
                 "Убедитесь, что в secrets.toml есть секции [car_numbers] и [cars].")
        st.stop()

# ------------------------------------------------------------
# 2. Основная логика (без изменений)
# ------------------------------------------------------------
def get_odometers(df_od, dt_date, car_numbers, cars_list):
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
# 5. Основной интерфейс (один экран)
# ------------------------------------------------------------
def main():
    st.set_page_config(page_title="Анализ пробега", layout="wide")
    st.title("📊 Анализ пробега автомобилей")

    init_session()

    # ---- Выбор месяца и года ----
    col1, col2 = st.columns(2)
    with col1:
        year = st.selectbox("Год", list(range(2020, 2030)), index=datetime.now().year - 2020)
    with col2:
        month = st.selectbox("Месяц", list(range(1, 13)), index=datetime.now().month - 1)

    last_day = calendar.monthrange(year, month)[1]
    dt_date = datetime(year, month, last_day)
    st.write(f"Выбрана дата: **{dt_date.strftime('%d.%m.%Y')}**")

    # ---- Кнопка загрузки и расчёта ----
    if st.button("📥 Загрузить данные и рассчитать"):
        with st.spinner("Загрузка данных из Google Sheets..."):
            df = load_data_from_gsheet()
            if df is not None:
                # Переименовываем колонки в нужные для логики
                df = df.rename(columns={
                    'Timestamp': 'time',
                    'Гос. номер автомобиля (только 3 цифры)': 'car_number',
                    'Текущий пробег (значение на одометре) (только число)': 'odometer'
                })
                # Проверяем наличие колонок после переименования
                required = ['time', 'car_number', 'odometer']
                if all(col in df.columns for col in required):
                    st.session_state.df_od = df
                    st.session_state.dt_date = dt_date
                    st.success(f"✅ Данные загружены ({len(df)} записей). Выполняется расчёт...")
                else:
                    st.error(f"❌ После переименования не хватает колонок: {required}")
                    st.write("Фактические колонки:", list(df.columns))
                    st.stop()
            else:
                st.stop()

        # ---- Расчёт ----
        with st.spinner("Выполняется расчёт..."):
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
                'logs': logs
            }
            st.success("✅ Расчёт завершён!")

    # ---- Отображение результатов ----
    res = st.session_state.results
    if res is not None:
        st.divider()
        st.header("📋 Результаты")

        # Вычисляем даты периодов (для вывода)
        dt = st.session_state.dt_date
        d1 = dt - timedelta(days=10)
        d2 = dt + timedelta(days=15)
        d3 = dt - timedelta(days=40)
        d4 = dt - timedelta(days=14)

        # ----- Текущий период -----
        st.subheader(f"Текущий период: {d1.strftime('%d.%m.%Y')} – {d2.strftime('%d.%m.%Y')}")
        col1, col2 = st.columns(2)
        with col1:
            st.write("**✅ Есть данные у машин:**")
            if res['d1_cars']:
                st.write(", ".join(res['d1_cars']))
            else:
                st.write("(нет)")
        with col2:
            st.write("**❌ Нет данных у машин:**")
            if res['diff_cur']:
                # Выводим список и телефоны
                for car in res['diff_cur']:
                    phone = st.session_state.car_numbers.get(car, "телефон не найден")
                    st.write(f"- {car} → {phone}")
            else:
                st.write("(все машины есть)")

        # ----- Предыдущий период -----
        st.subheader(f"Предыдущий период: {d3.strftime('%d.%m.%Y')} – {d4.strftime('%d.%m.%Y')}")
        col1, col2 = st.columns(2)
        with col1:
            st.write("**✅ Есть данные у машин:**")
            if res['d2_cars']:
                st.write(", ".join(res['d2_cars']))
            else:
                st.write("(нет)")
        with col2:
            st.write("**❌ Нет данных у машин:**")
            if res['diff_last']:
                for car in res['diff_last']:
                    phone = st.session_state.car_numbers.get(car, "телефон не найден")
                    st.write(f"- {car} → {phone}")
            else:
                st.write("(все машины есть)")

        # ----- Список телефонов для копирования (только из текущего периода) -----
        st.divider()
        st.subheader("📞 Телефоны машин без данных в ТЕКУЩЕМ периоде (для копирования)")
        phones_to_copy = []
        for car in res['diff_cur']:
            phone = st.session_state.car_numbers.get(car, "")
            if phone:
                phones_to_copy.append(phone)
        if phones_to_copy:
            # Выводим в виде текста, который легко скопировать
            phones_text = "\n".join(phones_to_copy)
            st.code(phones_text, language="text")
            st.caption("Скопируйте текст выше")
        else:
            st.info("Все машины есть в данных текущего периода.")

        # ---- (Опционально) Скачать Excel ----
        st.divider()
        st.subheader("💾 Скачать полный отчёт (Excel)")
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_res = pd.DataFrame(list(res['result_dict'].items()), columns=['Автомобиль', 'Разница пробега'])
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

if __name__ == "__main__":
    main()