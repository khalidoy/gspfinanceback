classDiagram
%% Embedded Documents
class ChangeDetail {
+String field_name
+String old_value
+String new_value
}

    class AgreedPayments {
        +Float m9_agreed
        +Float m10_agreed
        +Float m11_agreed
        +Float m12_agreed
        +Float m1_agreed
        +Float m2_agreed
        +Float m3_agreed
        +Float m4_agreed
        +Float m5_agreed
        +Float m6_agreed
        +Float m9_transport_agreed
        +Float m10_transport_agreed
        +Float m11_transport_agreed
        +Float m12_transport_agreed
        +Float m1_transport_agreed
        +Float m2_transport_agreed
        +Float m3_transport_agreed
        +Float m4_transport_agreed
        +Float m5_transport_agreed
        +Float m6_transport_agreed
        +Float insurance_agreed
    }

    class RealPayments {
        +Float m9_real
        +Float m10_real
        +Float m11_real
        +Float m12_real
        +Float m1_real
        +Float m2_real
        +Float m3_real
        +Float m4_real
        +Float m5_real
        +Float m6_real
        +Float m9_transport_real
        +Float m10_transport_real
        +Float m11_transport_real
        +Float m12_transport_real
        +Float m1_transport_real
        +Float m2_transport_real
        +Float m3_transport_real
        +Float m4_transport_real
        +Float m5_transport_real
        +Float m6_transport_real
        +Float insurance_real
    }

    class PaymentInfo {
        +AgreedPayments agreed_payments
        +RealPayments real_payments
    }

    class FixedExpense {
        +String expense_type
        +Float expense_amount
    }

    %% Primary Models
    class SchoolYearPeriod {
        +String name
        +DateTime start_date
        +DateTime end_date
        +to_json()
    }

    class User {
        +String username
        +String password_hash
        +set_password(password)
        +check_password(password)
        +to_json()
    }

    class Student {
        +String name
        +SchoolYearPeriod school_year
        +Boolean isNew
        +Boolean isLeft
        +Int joined_month
        +String observations
        +PaymentInfo payments
        +DateTime left_date
        +Boolean isSpecial
        +to_json()
    }

    class Save {
        +Student student
        +User user
        +DateTime date
        +List~String~ types
        +List~ChangeDetail~ changes
        +to_json()
    }

    class Depence {
        +String type
        +String description
        +DateTime date
        +List~FixedExpense~ fixed_expenses
        +Float amount
        +to_json()
    }

    class Payment {
        +Student student
        +User user
        +DateTime date
        +Float amount
        +String payment_type
        +Int month
        +to_json()
    }

    class DailyAccounting {
        +DateTime date
        +List~Payment~ payments
        +List~Depence~ daily_expenses
        +Float total_payments
        +Float total_expenses
        +Float net_profit
        +Boolean isValidated
        +calculate_totals()
        +to_json()
    }

    %% Relationships
    Student --> SchoolYearPeriod: school_year
    Save --> Student: student
    Save --> User: user
    Student *-- PaymentInfo: payments
    PaymentInfo *-- AgreedPayments: agreed_payments
    PaymentInfo *-- RealPayments: real_payments
    Save *-- ChangeDetail: changes
    Depence *-- FixedExpense: fixed_expenses
    Payment --> Student: student
    Payment --> User: user
    DailyAccounting --> Payment: payments
    DailyAccounting --> Depence: daily_expenses
