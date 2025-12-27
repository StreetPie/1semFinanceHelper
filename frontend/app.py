import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import time

st.set_page_config(
    page_title="Финансовый помощник",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

BACKEND_URL = "http://localhost:8000"

if 'token' not in st.session_state:
    st.session_state.token = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'user_id' not in st.session_state:
    st.session_state.user_id = None


def login_page():
    """Страница входа и регистрации"""
    st.title("Вход в систему")

    tab1, tab2 = st.tabs(["Вход", "Регистрация"])

    with tab1:
        with st.form("login_form"):
            username = st.text_input("Имя пользователя")
            password = st.text_input("Пароль", type="password")
            submit = st.form_submit_button("Войти")

            if submit:
                if not username or not password:
                    st.error("Заполните все поля")
                else:
                    try:
                        response = requests.post(
                            f"{BACKEND_URL}/login/",
                            json={"username": username, "password": password}
                        )

                        if response.status_code == 200:
                            data = response.json()
                            st.session_state.token = data['access_token']
                            st.session_state.username = username
                            st.success("Успешный вход!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Неверное имя пользователя или пароль")
                    except requests.exceptions.ConnectionError:
                        st.error("Не удалось подключиться к серверу. Запустите бэкенд!")

    with tab2:
        with st.form("register_form"):
            new_username = st.text_input("Имя пользователя")
            new_password = st.text_input("Пароль", type="password")
            confirm_password = st.text_input("Подтвердите пароль", type="password")
            submit = st.form_submit_button("Зарегистрироваться")

            if submit:
                if not new_username or not new_password:
                    st.error("Заполните все поля")
                elif new_password != confirm_password:
                    st.error("Пароли не совпадают")
                else:
                    try:
                        response = requests.post(
                            f"{BACKEND_URL}/register/",
                            json={"username": new_username, "password": new_password}
                        )

                        if response.status_code == 200:
                            st.success("Регистрация успешна! Теперь войдите в систему.")
                        else:
                            error_data = response.json()
                            st.error(f"Ошибка: {error_data.get('detail', 'Неизвестная ошибка')}")
                    except requests.exceptions.ConnectionError:
                        st.error("Не удалось подключиться к серверу. Запустите бэкенд!")


def get_auth_headers():
    if st.session_state.token:
        return {"Authorization": f"Bearer {st.session_state.token}"}
    return {}


def make_authenticated_request(method, endpoint, **kwargs):
    headers = get_auth_headers()
    if 'headers' in kwargs:
        kwargs['headers'].update(headers)
    else:
        kwargs['headers'] = headers

    try:
        response = requests.request(method, f"{BACKEND_URL}{endpoint}", **kwargs)
        return response
    except requests.exceptions.ConnectionError:
        return None


def logout():
    st.session_state.token = None
    st.session_state.username = None
    st.session_state.user_id = None
    st.rerun()


def main_dashboard():
    st.header("Общая статистика")

    try:
        response = make_authenticated_request("GET", "/stats/")

        if response and response.status_code == 200:
            stats = response.json()

            # Ключевые метрики
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Общий доход", f"{stats['total_income']:,.0f} ₽")
            with col2:
                st.metric("Общие расходы", f"{stats['total_expenses']:,.0f} ₽")
            with col3:
                st.metric("Баланс", f"{stats['balance']:,.0f} ₽")
            with col4:
                if stats['total_income'] > 0:
                    savings_rate = (stats['balance'] / stats['total_income'] * 100)
                else:
                    savings_rate = 0
                st.metric("Накопления", f"{savings_rate:.1f}%")

            trans_response = make_authenticated_request("GET", "/transactions/?limit=100")

            if trans_response and trans_response.status_code == 200:
                transactions = trans_response.json()

                col1, col2 = st.columns(2)

                with col1:
                    if stats['expenses_by_category']:
                        fig_pie = px.pie(
                            values=list(stats['expenses_by_category'].values()),
                            names=list(stats['expenses_by_category'].keys()),
                            title="Расходы по категориям",
                            hole=0.3
                        )
                        st.plotly_chart(fig_pie, use_container_width=True)

                with col2:
                    # График доходов/расходов по времени
                    if transactions:
                        df = pd.DataFrame(transactions)
                        if 'date' in df.columns and not df.empty:
                            df['date'] = pd.to_datetime(df['date'], errors='coerce')
                            df = df.dropna(subset=['date'])

                            if not df.empty:
                                df_weekly = df.groupby([pd.Grouper(key='date', freq='W'), 'type'])[
                                    'amount'].sum().reset_index()

                                fig_line = px.line(
                                    df_weekly,
                                    x='date',
                                    y='amount',
                                    color='type',
                                    title="Динамика доходов и расходов",
                                    labels={'amount': 'Сумма (₽)', 'date': 'Дата'}
                                )
                                st.plotly_chart(fig_line, use_container_width=True)

            st.subheader("Детализация по категориям")
            if stats['expenses_by_category']:
                col1, col2 = st.columns(2)

                with col1:
                    st.write("**Расходы по категориям:**")
                    for category, amount in stats['expenses_by_category'].items():
                        st.write(f"• {category}: {amount:,.0f} ₽")

                with col2:
                    # Бар-чарт
                    if stats['expenses_by_category']:
                        fig_bar = px.bar(
                            x=list(stats['expenses_by_category'].keys()),
                            y=list(stats['expenses_by_category'].values()),
                            title="Расходы по категориям",
                            labels={'x': 'Категория', 'y': 'Сумма (₽)'}
                        )
                        st.plotly_chart(fig_bar, use_container_width=True)

        elif response and response.status_code == 401:
            st.error("Ошибка авторизации. Пожалуйста, войдите заново.")
            logout()
        else:
            st.error("Ошибка загрузки данных")

    except Exception as e:
        st.error(f"Ошибка: {str(e)}")


def transactions_page():
    st.header("Управление транзакциями")

    with st.form("add_transaction"):
        col1, col2, col3 = st.columns(3)

        with col1:
            amount = st.number_input("Сумма", min_value=0.0, step=100.0, value=0.0)
            transaction_type = st.selectbox(
                "Тип",
                ["expense", "income"],
                format_func=lambda x: "📉 Расход" if x == "expense" else "📈 Доход"
            )

        with col2:
            category = st.selectbox("Категория", [
                "Еда", "Транспорт", "Развлечения", "Коммунальные",
                "Здоровье", "Образование", "Другое", "Зарплата",
                "Фриланс", "Инвестиции", "Подарки"
            ])
            date = st.date_input("Дата", value=datetime.now())

        with col3:
            description = st.text_input("Описание", placeholder="Краткое описание...")

        submit = st.form_submit_button("Добавить транзакцию")

        if submit:
            if amount > 0:
                transaction_data = {
                    "amount": float(amount),
                    "type": transaction_type,
                    "category": category,
                    "description": description,
                    "date": date.isoformat()
                }

                response = make_authenticated_request("POST", "/transactions/", json=transaction_data)

                if response and response.status_code == 200:
                    st.success("Транзакция успешно добавлена!")
                    time.sleep(1)
                    st.rerun()
                elif response and response.status_code == 401:
                    st.error("Ошибка авторизации")
                    logout()
                else:
                    st.error("Ошибка при добавлении транзакции")
            else:
                st.warning("Введите сумму больше 0")

    st.subheader("История транзакций") #список

    try:
        response = make_authenticated_request("GET", "/transactions/")

        if response and response.status_code == 200:
            transactions = response.json()

            if transactions:
                # Фильтры
                col1, col2, col3 = st.columns(3)
                with col1:
                    filter_type = st.selectbox("Фильтр по типу", ["Все", "Доходы", "Расходы"])
                with col2:
                    filter_category = st.selectbox("Фильтр по категории",
                                                   ["Все"] + sorted(list(set(t['category'] for t in transactions))))
                with col3:
                    search_text = st.text_input("Поиск по описанию")

                filtered_transactions = transactions

                if filter_type == "Доходы":
                    filtered_transactions = [t for t in filtered_transactions if t['type'] == 'income']
                elif filter_type == "Расходы":
                    filtered_transactions = [t for t in filtered_transactions if t['type'] == 'expense']

                if filter_category != "Все":
                    filtered_transactions = [t for t in filtered_transactions if t['category'] == filter_category]

                if search_text:
                    filtered_transactions = [t for t in filtered_transactions
                                             if search_text.lower() in t.get('description', '').lower()]

                # Отображение таблицы
                df = pd.DataFrame(filtered_transactions)
                if not df.empty:
                    if 'created_at' in df.columns:
                        df['created_at'] = pd.to_datetime(df['created_at'])
                        df = df.sort_values('created_at', ascending=False) #сорт

                    df['Тип'] = df['type'].apply(lambda x: ' Доход' if x == 'income' else 'Расход') #форматирование
                    df['Сумма'] = df['amount'].apply(lambda x: f"{x:,.0f} ₽")
                    df['Дата'] = pd.to_datetime(df['date']).dt.strftime('%d.%m.%Y')
                    df['Добавлено'] = pd.to_datetime(df['created_at']).dt.strftime('%d.%m.%Y %H:%M')

                    display_cols = ['Тип', 'Категория', 'Сумма', 'Описание', 'Дата', 'Добавлено']
                    display_cols = [col for col in display_cols if col in df.columns]

                    st.dataframe(
                        df[display_cols],
                        use_container_width=True,
                        hide_index=True
                    )

                    # Суммарная статистика
                    total_income = sum(t['amount'] for t in filtered_transactions if t['type'] == 'income')
                    total_expense = sum(t['amount'] for t in filtered_transactions if t['type'] == 'expense')

                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Сумма доходов в выборке", f"{total_income:,.0f} ₽")
                    with col2:
                        st.metric("Сумма расходов в выборке", f"{total_expense:,.0f} ₽")
                else:
                    st.info("Нет транзакций, соответствующих фильтрам")
            else:
                st.info("Транзакций пока нет")
        elif response and response.status_code == 401:
            st.error("Ошибка авторизации")
            logout()
        else:
            st.error("Ошибка загрузки транзакций")

    except Exception as e:
        st.error(f"Ошибка: {str(e)}")


def budgets_page():
    st.header("Бюджеты и лимиты")

    # Форма создания бюджета
    with st.form("add_budget"):
        st.subheader("Создать новый бюджет")

        col1, col2, col3 = st.columns(3)

        with col1:
            category = st.selectbox("Категория бюджета", [
                "Еда", "Транспорт", "Развлечения", "Коммунальные",
                "Здоровье", "Образование", "Другое"
            ], key="budget_category")

        with col2:
            limit_amount = st.number_input("Лимит в месяц", min_value=0.0, step=1000.0, value=10000.0)

        with col3:
            period = st.selectbox("Период", ["monthly"], disabled=True)

        submit = st.form_submit_button("Создать бюджет")

        if submit:
            budget_data = {
                "category": category,
                "limit_amount": float(limit_amount),
                "period": period
            }

            response = make_authenticated_request("POST", "/budgets/", json=budget_data)

            if response and response.status_code == 200:
                st.success("Бюджет успешно создан!")
                time.sleep(1)
                st.rerun()
            elif response and response.status_code == 401:
                st.error("Ошибка авторизации")
                logout()
            else:
                st.error("Ошибка при создании бюджета")

    # Список бюджетов
    st.subheader("Ваши бюджеты")

    try:
        response = make_authenticated_request("GET", "/budgets/")

        if response and response.status_code == 200:
            budgets = response.json()

            if budgets:
                trans_response = make_authenticated_request("GET", "/transactions/")
                transactions = trans_response.json() if trans_response and trans_response.status_code == 200 else []

                for budget in budgets:
                    category = budget['category']
                    limit = budget['limit_amount']

                    spent = sum(t['amount'] for t in transactions
                                if t['category'] == category and t['type'] == 'expense')

                    # Прогресс бар
                    progress = min(spent / limit, 1.0) if limit > 0 else 0

                    col1, col2, col3, col4 = st.columns([2, 1, 2, 1])

                    with col1:
                        st.write(f"**{category}**")

                    with col2:
                        st.write(f"Лимит: {limit:,.0f} ₽")

                    with col3:
                        st.progress(progress)
                        st.write(f"Потрачено: {spent:,.0f} ₽ ({progress:.1%})")

                    with col4:
                        if spent > limit:
                            st.error("Перерасход!")
                        elif progress > 0.8:
                            st.warning(" Близко к лимиту")
                        elif progress > 0:
                            st.success("В норме")
                        else:
                            st.info("Нет трат")

                    st.markdown("---")
            else:
                st.info("Бюджеты не настроены. Создайте первый бюджет выше.")

        elif response and response.status_code == 401:
            st.error("Ошибка авторизации")
            logout()
        else:
            st.error("Ошибка загрузки бюджетов")

    except Exception as e:
        st.error(f"Ошибка: {str(e)}")


def analytics_page():
    st.header("Финансовая аналитика")

    try:
        response = make_authenticated_request("GET", "/stats/")

        if response and response.status_code == 200:
            stats = response.json()

            # Аналитические выводы
            st.subheader("Рекомендации")

            if stats['total_income'] > 0:
                savings_rate = (stats['balance'] / stats['total_income']) * 100

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.markdown("#### Норма накоплений")
                    if savings_rate < 10:
                        st.error("Низкая")
                        st.write("< 10% от доходов")
                    elif savings_rate > 20:
                        st.success("Отличная!")
                        st.write("Вы откладываете более 20% доходов")
                    else:
                        st.warning("Хорошая")
                        st.write("в пределах от 10% до 20%")

                with col2:
                    st.markdown("#### Основные расходы")
                    if stats['expenses_by_category']:
                        max_category = max(stats['expenses_by_category'].items(), key=lambda x: x[1])
                        st.info(f"**{max_category[0]}**")
                        st.write(f"{max_category[1]:,.0f} ₽")
                    else:
                        st.info("Нет данных о расходах")

                with col3:
                    st.markdown("#### Баланс")
                    if stats['balance'] < 0:
                        st.error("**Отрицательный**")
                        st.write("Расходы превышают доходы!")
                    else:
                        st.success("**Положительный**")
                        st.write("Финансы под контролем")

            st.subheader("Анализ")

            if stats['expenses_by_category']:
                expenses_df = pd.DataFrame(
                    list(stats['expenses_by_category'].items()),
                    columns=['Категория', 'Сумма']
                )
                expenses_df['Доля'] = (expenses_df['Сумма'] / expenses_df['Сумма'].sum() * 100).round(1)
                expenses_df = expenses_df.sort_values('Сумма', ascending=False)

                st.dataframe(expenses_df, use_container_width=True)

                if len(expenses_df) > 0:
                    largest_category = expenses_df.iloc[0]['Категория']
                    largest_amount = expenses_df.iloc[0]['Сумма']
                    largest_share = expenses_df.iloc[0]['Доля']

                    st.info(f"""
                    Совет по оптимизации:

                    Основная статья расходов - {largest_category}** ({largest_share}% всех расходов).

                    Рекомендации:
                    - Проанализируйте траты в категории "{largest_category}"
                    - Подумайте, где можно сократить расходы либо установите лимит для этой категории
                    """)

        elif response and response.status_code == 401:
            st.error("Ошибка авторизации")
            logout()
        else:
            st.error("Ошибка загрузки аналитики")

    except Exception as e:
        st.error(f"Ошибка: {str(e)}")


def profile_page():
    st.header("Профиль пользователя")

    st.write(f"**Имя пользователя:** {st.session_state.username}")
    st.write(f"**Токен авторизации:**")
    st.code(st.session_state.token[:50] + "..." if st.session_state.token else "Нет токена")

    # Информация о пользователе
    try:
        response = make_authenticated_request("GET", "/me/")
        if response and response.status_code == 200:
            user_data = response.json()
            st.write(f"**ID пользователя:** {user_data.get('id', 'Неизвестно')}")
            st.write(f"**Роль:** {user_data.get('role', 'user')}")
        else:
            st.warning("Не удалось загрузить полную информацию о пользователе")
    except:
        pass

    if st.button("Выйти из системы", type="primary"):
        logout()



def main():

    if not st.session_state.token: #авторизация
        login_page()
        return


    # Боковая панель навигации
    with st.sidebar:
        st.title(f"Привет, {st.session_state.username}!")

        pages = {
            "Дашборд": main_dashboard,
            "Транзакции": transactions_page,
            "Бюджеты": budgets_page,
            "Аналитика": analytics_page,
            "Профиль": profile_page
        }

        selected_page = st.radio("Навигация", list(pages.keys()))

        st.markdown("---")

        st.info("""
         Учебный проект: Финансовый помощник. 
         Опарин Д.Г. 6В51ПИШ

        По вопросам: bob604604@gmail.com
        Зачет проставлять
        """)

        if st.button("Выйти", key="sidebar_logout"):
            logout()

    pages[selected_page]()


if __name__ == "__main__":
    main()