from sqladmin import ModelView

from src.database.models import AssembledMessages, Person, WeeklySummary


class AssembledMessageAdmin(ModelView, model=AssembledMessages):
    name, name_plural = "Заметка", "Заметки"
    column_list = [AssembledMessages.id, AssembledMessages.session_id,
                   AssembledMessages.message_thread, AssembledMessages.status,
                   AssembledMessages.title, AssembledMessages.created_at]
    column_searchable_list = [AssembledMessages.title, AssembledMessages.summary]
    column_sortable_list = [AssembledMessages.id, AssembledMessages.created_at, AssembledMessages.status]
    # embedding — огромный вектор, прячем из деталей и формы
    column_details_exclude_list = [AssembledMessages.embedding]
    form_excluded_columns = [AssembledMessages.embedding]
    page_size = 25


class PersonAdmin(ModelView, model=Person):
    name, name_plural = "Персона", "Персоны"
    column_list = [Person.id, Person.name, Person.role, Person.first_seen, Person.last_seen]
    column_searchable_list = [Person.name]
    column_sortable_list = [Person.name, Person.last_seen]
    page_size = 50


class WeeklySummaryAdmin(ModelView, model=WeeklySummary):
    name, name_plural = "Сводка", "Сводки"
    column_list = [WeeklySummary.id, WeeklySummary.period_start,
                   WeeklySummary.period_end, WeeklySummary.sent_to_telegram]
    column_sortable_list = [WeeklySummary.period_end]
    page_size = 25