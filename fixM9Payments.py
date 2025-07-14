from models import Student, SchoolYearPeriod
from mongoengine import connect
import sys
from dotenv import load_dotenv
import os

# Connect to local MongoDB
MONGO_URI = "mongodb+srv://khalid:Khayamowa6@cluster0.8urff.mongodb.net/gspFinance"

def connect_db():
    try:
        connect(host=MONGO_URI)
        print("Connected to development MongoDB")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        sys.exit(1)

def check_m9_m10_differences():
    different_students = []
    
    # Get all students who joined in September (month 9)
    students = Student.objects(joined_month=9)
    
    for student in students:
        if not student.payments:
            continue
            
        real = student.payments.real_payments
        agreed = student.payments.agreed_payments
        
        # Add transport info for all months in school year order
        transport_info = []
        # First semester (M9-M12)
        for month in range(9, 13):
            month_str = f'm{month}'
            real_transport = getattr(real, f'{month_str}_transport_real', 0) or 0
            agreed_transport = getattr(agreed, f'{month_str}_transport_agreed', 0) or 0
            if real_transport > 0 or agreed_transport > 0:
                transport_info.append(f"M{month}: Real=${real_transport}, Agreed=${agreed_transport}")
        
        # Second semester (M1-M6)
        for month in range(1, 7):
            month_str = f'm{month}'
            real_transport = getattr(real, f'{month_str}_transport_real', 0) or 0
            agreed_transport = getattr(agreed, f'{month_str}_transport_agreed', 0) or 0
            if real_transport > 0 or agreed_transport > 0:
                transport_info.append(f"M{month}: Real=${real_transport}, Agreed=${agreed_transport}")
        
        # Add regular payment info for school year order
        payment_info = []
        # First semester (M9-M12)
        for month in range(9, 13):
            month_str = f'm{month}'
            real_payment = getattr(real, f'{month_str}_real', 0) or 0
            agreed_payment = getattr(agreed, f'{month_str}_agreed', 0) or 0
            payment_info.append(f"M{month}: Real=${real_payment}, Agreed=${agreed_payment}")
        
        # Second semester (M1-M6)
        for month in range(1, 7):
            month_str = f'm{month}'
            real_payment = getattr(real, f'{month_str}_real', 0) or 0
            agreed_payment = getattr(agreed, f'{month_str}_agreed', 0) or 0
            payment_info.append(f"M{month}: Real=${real_payment}, Agreed=${agreed_payment}")

        # Original discrepancy checks
        discrepancies = []
        has_discrepancy = False
        
        # Check monthly payments - only if M10 is not 0
        m9_real = real.m9_real or 0
        m10_real = real.m10_real or 0
        if m10_real != 0 and m9_real != m10_real:
            discrepancies.append(f"Monthly: M9=${m9_real} ≠ M10=${m10_real}")
            has_discrepancy = True
            
        # Check agreed payments - only if M10 is not 0
        m9_agreed = agreed.m9_agreed or 0
        m10_agreed = agreed.m10_agreed or 0
        if m10_agreed != 0 and m9_agreed != m10_agreed:
            discrepancies.append(f"Agreed Monthly: M9=${m9_agreed} ≠ M10=${m10_agreed}")
            has_discrepancy = True
        
        if has_discrepancy:
            different_students.append({
                'student_name': student.name,
                'discrepancies': discrepancies,
                'transport_info': transport_info,
                'payment_info': payment_info,
                'id': str(student.id)
            })
    
    # Print results with all payment information
    print(f"\nFound {len(different_students)} students with different M9/M10 payments:")
    print("=" * 70)
    
    for student in different_students:
        print(f"\nStudent: {student['student_name']} (ID: {student['id']})")
        print("\nDiscrepancies:")
        for discrepancy in student['discrepancies']:
            print(f"  - {discrepancy}")
        print("\nMonthly Payments:")
        for payment in student['payment_info']:
            print(f"  - {payment}")
        print("\nTransport Payments:")
        for transport in student['transport_info']:
            print(f"  - {transport}")
        print("-" * 50)
    
    print(f"\nTotal students with differences: {len(different_students)}")

def fix_m9_payments():
    fixed_count = 0
    
    # Get all students who joined in September (month 9)
    students = Student.objects(joined_month=9)
    
    for student in students:
        if not student.payments:
            continue
            
        real = student.payments.real_payments
        agreed = student.payments.agreed_payments
        needs_update = False
        
        # Track the transport amount to propagate
        transport_to_propagate = 0
        
        # First semester (M9-M12)
        for current_month in range(9, 13):
            next_month = current_month + 1 if current_month < 12 else 1
            
            current_real = getattr(real, f'm{current_month}_real', 0) or 0
            next_real = getattr(real, f'm{next_month}_real', 0) or 0
            
            if current_real != 0 and next_real > current_real:
                transport_amount = next_real - current_real
                monthly_amount = current_real
                transport_to_propagate = transport_amount  # Remember this transport amount
                
                # Print before state
                print(f"\nFixing {student.name}'s M{current_month}/M{next_month} payments:")
                print("Before:")
                print(f"  M{current_month}: Monthly=${current_real}, Transport=${getattr(real, f'm{current_month}_transport_real', 0) or 0}")
                print(f"  M{next_month}: Monthly=${next_real}, Transport=${getattr(real, f'm{next_month}_transport_real', 0) or 0}")
                
                # Set the split payments
                setattr(real, f'm{current_month}_real', monthly_amount)
                setattr(real, f'm{current_month}_transport_real', transport_amount)
                setattr(agreed, f'm{current_month}_agreed', monthly_amount)
                setattr(agreed, f'm{current_month}_transport_agreed', transport_amount)
                
                setattr(real, f'm{next_month}_real', monthly_amount)
                setattr(real, f'm{next_month}_transport_real', transport_amount)
                setattr(agreed, f'm{next_month}_agreed', monthly_amount)
                setattr(agreed, f'm{next_month}_transport_agreed', transport_amount)
                
                # Propagate transport to remaining months in first semester
                for future_month in range(current_month + 2, 13):
                    setattr(agreed, f'm{future_month}_transport_agreed', transport_amount)
                
                # Propagate transport to second semester
                for future_month in range(1, 7):
                    setattr(agreed, f'm{future_month}_transport_agreed', transport_amount)
                
                needs_update = True
                
                # Print after state with propagation info
                print("After:")
                print(f"  M{current_month}: Monthly=${monthly_amount}, Transport=${transport_amount}")
                print(f"  M{next_month}: Monthly=${monthly_amount}, Transport=${transport_amount}")
                print(f"  Transport fee of ${transport_amount} propagated to all subsequent months")
                print("-" * 50)
        
        # Second semester (M1-M6) - handle any new changes but keep propagated transport
        for current_month in range(1, 6):
            next_month = current_month + 1
            
            current_real = getattr(real, f'm{current_month}_real', 0) or 0
            next_real = getattr(real, f'm{next_month}_real', 0) or 0
            
            if current_real != 0 and next_real > current_real:
                new_transport = next_real - current_real
                monthly_amount = current_real
                
                # Use the larger transport amount between new and propagated
                transport_amount = max(new_transport, transport_to_propagate)
                
                # Print before state
                print(f"\nFixing {student.name}'s M{current_month}/M{next_month} payments:")
                print("Before:")
                print(f"  M{current_month}: Monthly=${current_real}, Transport=${getattr(real, f'm{current_month}_transport_real', 0) or 0}")
                print(f"  M{next_month}: Monthly=${next_real}, Transport=${getattr(real, f'm{next_month}_transport_real', 0) or 0}")
                
                # Set the split payments
                setattr(real, f'm{current_month}_real', monthly_amount)
                setattr(real, f'm{current_month}_transport_real', transport_amount)
                setattr(agreed, f'm{current_month}_agreed', monthly_amount)
                setattr(agreed, f'm{current_month}_transport_agreed', transport_amount)
                
                setattr(real, f'm{next_month}_real', monthly_amount)
                setattr(real, f'm{next_month}_transport_real', transport_amount)
                setattr(agreed, f'm{next_month}_agreed', monthly_amount)
                setattr(agreed, f'm{next_month}_transport_agreed', transport_amount)
                
                # Propagate transport to remaining months
                for future_month in range(current_month + 2, 7):
                    setattr(agreed, f'm{future_month}_transport_agreed', transport_amount)
                
                needs_update = True
                print("After:")
                print(f"  M{current_month}: Monthly=${monthly_amount}, Transport=${transport_amount}")
                print(f"  M{next_month}: Monthly=${monthly_amount}, Transport=${transport_amount}")
                print(f"  Transport fee of ${transport_amount} propagated to all subsequent months")
                print("-" * 50)
        
        if needs_update:
            student.save()
            fixed_count += 1
    
    print(f"\nFixed payments for {fixed_count} students")

def propagate_m9_transport():
    fixed_count = 0
    
    # Get all students who joined in September (month 9)
    students = Student.objects(joined_month=9)
    
    for student in students:
        if not student.payments:
            continue
            
        real = student.payments.real_payments
        agreed = student.payments.agreed_payments
        
        # Check if student has M9 transport
        m9_transport = real.m9_transport_real or 0
        if m9_transport > 0:
            needs_update = False
            print(f"\nChecking {student.name}'s M9 transport propagation:")
            print(f"M9 transport amount: ${m9_transport}")
            
            # Propagate to M10-M12
            for month in range(10, 13):
                current_agreed = getattr(agreed, f'm{month}_transport_agreed', 0) or 0
                if current_agreed != m9_transport:
                    print(f"  Updating M{month} transport agreed: ${current_agreed} -> ${m9_transport}")
                    setattr(agreed, f'm{month}_transport_agreed', m9_transport)
                    needs_update = True
            
            # Propagate to M1-M6
            for month in range(1, 7):
                current_agreed = getattr(agreed, f'm{month}_transport_agreed', 0) or 0
                if current_agreed != m9_transport:
                    print(f"  Updating M{month} transport agreed: ${current_agreed} -> ${m9_transport}")
                    setattr(agreed, f'm{month}_transport_agreed', m9_transport)
                    needs_update = True
            
            if needs_update:
                student.save()
                fixed_count += 1
                print("  Changes saved!")
            else:
                print("  No changes needed - transport already propagated")
    
    print(f"\nPropagated M9 transport fees for {fixed_count} students")

if __name__ == "__main__":
    print("Starting M9 payment fixes on development database...")
    connect_db()
    check_m9_m10_differences()  # First check the differences
    print("\nNow fixing the payments...")
    fix_m9_payments()           # Then fix them
    print("\nPropagating M9 transport fees...")
    propagate_m9_transport()    # Propagate M9 transport
    print("\nChecking remaining differences...")
    check_m9_m10_differences()  # Check again to verify fixes
    print("Finished")
