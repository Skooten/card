from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_cors import CORS
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, relationship, declarative_base, joinedload
from sqlalchemy.exc import IntegrityError
from psycopg2.errors import UniqueViolation
from datetime import datetime
import logging
from urllib.parse import quote_plus
from sqlalchemy.sql import text
from database import DATABASE_URL
from models import Act, Base, BuildingDepartment, Cartridge, CartridgeEntry, Department, Model, Service, Status
engine = create_engine(DATABASE_URL, echo=False)


app = Flask(__name__)
CORS(app)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

logging.basicConfig(filename='app.log', level=logging.INFO)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cartridges', methods=['GET', 'POST'])
def cartridges():
    db = SessionLocal()
    message = None
    cartridge_entry = None
    cartridge = None
    department_info = None
    service = None
    act = None
    acts = None
    new_service_exists = False
    show_button = False

    barcode = request.form.get('barcode') if request.method == 'POST' else request.args.get('barcode')

    if barcode:
        try:
            cartridge_entry = db.query(CartridgeEntry).filter(CartridgeEntry.barCode == barcode).first()

            if cartridge_entry is None:
                message = f"Картридж со штрихкодом '{barcode}' не найден."
            else:
                cartridge = cartridge_entry.cartridge
                building_department = db.query(BuildingDepartment).filter(BuildingDepartment.builddep_id == cartridge_entry.builddep_id).first()

                if building_department:
                    department_name = building_department.department.name
                    building_name = building_department.building.name
                    department_info = f"{building_name} - {department_name}"
                else:
                    department_info = "Нет данных"

                service = db.query(Service).filter(Service.barCode == barcode).order_by(Service.date_in.desc(), Service.service_id.desc()).first()

                if service:
                    act = db.query(Act).filter(Act.act_id == service.act_id).first()

                    # Проверка наличия новой записи после отправки на заправку
                    new_service_exists = db.query(Service).filter(Service.barCode == barcode).filter(Service.date_in > service.date_in).first() is not None


                    if not (service.date_in or service.date_out or service.date_recieve or service.date_get or service.weight_in or service.weight_out or service.who_get):
                        show_button = True
                else:
                    show_button = True

                acts = db.query(Act).all()

        except Exception as e:
            db.rollback()
            message = f"Произошла ошибка: {e}"
            logging.error(f"Ошибка в cartridges: {e}")
    try:
        cartridges = db.query(Cartridge).all()
        departments = db.query(BuildingDepartment).all()
        # Если acts все еще None, присвойте ему пустой список
        if acts is None:
            acts = []
        # Рендерим шаблон с данными, даже если их нет
        return render_template('cartridges.html',
                               cartridge_entry=cartridge_entry,
                               cartridge=cartridge,
                               department_info=department_info,
                               message=message,
                               cartridges=cartridges,
                               departments=departments,
                               service=service,
                               act=act,
                               acts=acts,
                               barcode=barcode,
                               service_id=service.service_id if service else None,
                               new_service_exists=new_service_exists,
                               show_button=show_button)  # Добавляем информацию о кнопке
    except Exception as e:
        logging.error(f"Ошибка при рендеринге шаблона cartridges.html: {e}")
        return f"Произошла ошибка при рендеринге страницы: {e}"
    finally:
        db.close()

@app.route('/update_cartridge_info', methods=['POST'])
def update_cartridge_info():
    barcode = request.form.get('barCode')
    date_in = request.form.get('date_in_department')
    weight_in_department = request.form.get('weight_in_department')
    date_out = request.form.get('date_out')
    date_recieve = request.form.get('date_recieve')
    date_get = request.form.get('date_get')
    weight_out = request.form.get('weight_out')
    weight_in = request.form.get('weight_in')
    who_get = request.form.get('who_get')
    act_id = request.form.get('act_id')
    send_to_refill = request.form.get('send_to_refill')
    recieve_from_service = request.form.get('recieve_from_service')
    give_to_employee = request.form.get('give_to_employee')
    prepare_to_send = request.form.get('prepare_to_send')
    status_id = request.form.get('status_id')
    create_first_service = request.form.get('create_first_service')

    db = SessionLocal()
    try:
        service = db.query(Service).filter(Service.barCode == barcode).order_by(Service.date_in.desc()).first()
        cartridge_entry = db.query(CartridgeEntry).filter(CartridgeEntry.barCode == barcode).first()

        if not service and create_first_service == 'true':
            if not weight_in or not who_get:
                return "Ошибка: Необходимо указать вес и кому выдали.", 400

            service = Service(
                barCode=barcode,
                date_in=datetime.now(),
                date_out=datetime.now(),
                date_recieve=datetime.now(),
                date_get=datetime.now(),
                weight_in=float(weight_in),
                weight_out=float(weight_in),
                who_get=who_get,  # Сохраняем who_get в базе данных
                act_id=1
            )
            db.add(service)
            db.commit()
            return redirect(url_for('cartridges', barcode=barcode))

        if not cartridge_entry:
            return "Ошибка: CartridgeEntry не найден", 400

        service = db.query(Service).filter(Service.barCode == barcode).order_by(Service.date_in.desc()).first()

        if status_id:
            cartridge_entry.status_id = int(status_id)

        if prepare_to_send == 'true':
            logging.info(f'Кнопка "Положить в коробку для отправки в СЦ" нажата для {barcode}')

            try:
                if date_in:
                    service.date_in = datetime.strptime(date_in, '%Y-%m-%dT%H:%M')
                if weight_out:
                    service.weight_out = float(weight_out)
                if act_id:
                    service.act_id = int(act_id)

                db.commit()
                logging.info(f"Данные для {barcode} успешно обновлены.")
            except Exception as e:
                db.rollback()
                logging.error(f"Ошибка при обновлении данных для {barcode}: {e}")
                return f"Ошибка: {str(e)}", 500

        elif recieve_from_service == 'true':
            logging.info(f'Кнопка "Получить из СЦ" нажата для {barcode}')

            if weight_in:
                service.weight_in = float(weight_in)

            service.date_recieve = datetime.now()

        elif send_to_refill == 'true':
            logging.info(f'Кнопка "Отправить на заправку" нажата для {barcode}')

            # Удалите существующую запись, если она есть
            existing_service = db.query(Service).filter(Service.barCode == barcode).order_by(Service.date_in.desc()).first()
            if existing_service:
                db.delete(existing_service)

            # Создать новую запись
            new_service = Service(
                barCode=barcode,
                date_in=datetime.now(),
                date_out=None,
                date_recieve=None,
                date_get=None,
                weight_in=None,
                weight_out=None,
                who_get=None,
                act_id=None
            )
            db.add(new_service)

            latest_service = db.query(Service).filter(Service.barCode == barcode).order_by(Service.date_in.desc()).first()

            if act_id and latest_service:
                latest_service.act_id = int(act_id)

        elif give_to_employee == 'true':
            logging.info(f'Кнопка "Выдать сотруднику" нажата для {barcode}')

            if service.date_in and service.date_out and service.date_recieve and service.weight_in and service.weight_out and service.act_id:
                if date_get:
                    service.date_get = datetime.strptime(date_get, '%Y-%m-%dT%H:%M')
                if who_get:
                    service.who_get = who_get
            else:
                return f"Ошибка: Не все необходимые поля заполнены.", 400

        else:
            if date_in:
                service.date_in = datetime.strptime(date_in, '%Y-%m-%dT%H:%M')
            if weight_in_department:
                service.weight_in = float(weight_in_department) if weight_in_department else None
            if date_out:
                service.date_out = datetime.strptime(date_out, '%Y-%m-%dT%H:%M') if date_out else None
            if date_recieve:
                service.date_recieve = datetime.strptime(date_recieve, '%Y-%m-%dT%H:%M') if date_recieve else None
            if date_get:
                service.date_get = datetime.strptime(date_get, '%Y-%m-%dT%H:%M') if date_get else None
            if weight_out:
                service.weight_out = float(weight_out) if weight_out else None
            if weight_in:
                service.weight_in = float(weight_in) if weight_in else None
            if who_get:
                service.who_get = who_get
            if act_id:
                service.act_id = int(act_id) if act_id else None

        db.commit()
        return redirect(url_for('cartridges', barcode=barcode))

    except IntegrityError as e:
        db.rollback()
        if isinstance(e.orig, UniqueViolation):
            db.execute(text("SELECT setval('services_service_id_seq', (SELECT MAX(service_id) FROM services))"))
            db.commit()
            logging.error("Исправлена последовательность service_id")
            return redirect(url_for('cartridges', barcode=barcode))
        else:
            return f"Ошибка базы данных: {str(e)}", 500

    except Exception as e:
        db.rollback()
        return f"Ошибка: {str(e)}", 500

    finally:
        db.close()

@app.route('/service/arrived_today', methods=['GET', 'POST'])
def arrived_today():
    db = SessionLocal()
    try:
        today = datetime.now().date()
        selected_date = today
        if request.method == 'POST':
            selected_date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()

        arrived_cartridges = db.query(Service).filter(
            func.date(Service.date_recieve) == selected_date,
            Service.date_get == None,
            Service.who_get == None
        ).all()

        print(f"Найдено картриджей: {len(arrived_cartridges)}")

        return render_template('arrived_today.html', cartridges=arrived_cartridges, selected_date=selected_date)
    except Exception as e:
        logging.error(f"Ошибка при рендеринге шаблона arrived_today.html: {e}")
        return f"Произошла ошибка при рендеринге страницы: {e}"
    finally:
        db.close()

@app.route('/send_to_sc', methods=['GET', 'POST'])
def send_to_sc():
    db = SessionLocal()
    cartridges = None

    if request.method == 'POST':
        try:
            barcodes = request.form.getlist('barcodes[]')
            for barcode in barcodes:
                service = db.query(Service).filter(Service.barCode == barcode).order_by(Service.date_in.desc()).first()
                if service:
                    service.date_out = datetime.now()
                    service.date_recieve = None
                    service.date_get = None
                    service.weight_in = None
                    service.who_get = None
            db.commit()
            return "Картриджи успешно отправлены в СЦ."
        except Exception as e:
            db.rollback()
            return f"Произошла ошибка: {e}"

    try:
        cartridges = db.query(CartridgeEntry).all()
        services = db.query(Service).all()
        ready_to_send = []

        for cartridge in cartridges:
            service = db.query(Service).filter(Service.barCode == cartridge.barCode).order_by(Service.date_in.desc()).first()
            if service and service.date_in and service.weight_out and service.act_id and not service.date_out:
                ready_to_send.append({
                    'cartridge': cartridge,
                    'service': service,
                    'department': cartridge.building_department.department.name if cartridge.building_department else 'Нет данных',
                    'building': cartridge.building_department.building.name if cartridge.building_department else 'Нет данных'
                })

        return render_template('send_to_sc.html', cartridges=ready_to_send)
    except Exception as e:
        logging.error(f"Ошибка при рендеринге шаблона send_to_sc.html: {e}")
        return f"Произошла ошибка при рендеринге страницы: {e}"
    finally:
        db.close()

@app.route('/service/cartridge_v_sc')
def cartridge_v_sc():
    db = SessionLocal()
    try:
        cartridges_in_sc = db.query(Service).join(CartridgeEntry, Service.barCode == CartridgeEntry.barCode).filter(
            Service.date_in != None,
            Service.weight_out != None,
            Service.act_id != None,
            Service.date_out != None,
            Service.date_recieve == None,
            CartridgeEntry.status_id == 3 
        ).all()

        return render_template('cartridge_v_sc.html', cartridges=cartridges_in_sc)
    except Exception as e:
        logging.error(f"Ошибка при рендеринге шаблона cartridge_v_sc.html: {e}")
        return f"Произошла ошибка при рендеринге страницы: {e}"
    finally:
        db.close()

@app.route('/service/spis')
def spis():

    db = SessionLocal()
    try:
        barcode = request.args.get('barcode')
        
        if barcode:
            cartridges = db.query(CartridgeEntry).options(
                joinedload(CartridgeEntry.cartridge),
                joinedload(CartridgeEntry.building_department).joinedload(BuildingDepartment.department)
            ).filter(CartridgeEntry.status_id == 4, CartridgeEntry.barCode.like(f'%{barcode}%')).all()
        else:
            cartridges = db.query(CartridgeEntry).options(
                joinedload(CartridgeEntry.cartridge),
                joinedload(CartridgeEntry.building_department).joinedload(BuildingDepartment.department)
            ).filter(CartridgeEntry.status_id == 4).all()

        return render_template('spis.html', cartridges=cartridges)
    except Exception as e:
        logging.error(f"Ошибка при рендеринге шаблона spis.html: {e}")
        return f"Произошла ошибка при рендеринге страницы: {e}"
    finally:
        db.close()

@app.route('/cartridge_edit', methods=['GET', 'POST'])
def cartridge_edit():
    if request.method == 'GET':
        barcode = request.args.get('barcode')
        if not barcode:
            return "Штрих-код не передан", 400

        db = SessionLocal()
        try:
            cartridge_entry = db.query(CartridgeEntry).filter(CartridgeEntry.barCode == barcode).first()

            if not cartridge_entry:
                return f"Картридж с штрих-кодом {barcode} не найден", 404

            cartridges = db.query(Cartridge).all()
            departments = db.query(BuildingDepartment).all()
            building_department = db.query(BuildingDepartment).filter(
                BuildingDepartment.builddep_id == cartridge_entry.builddep_id
            ).first()
            
            date_in_iso = cartridge_entry.date_in.strftime('%Y-%m-%dT%H:%M') if cartridge_entry.date_in else None

            return render_template('cartridge_edit.html',
                                   barcode=cartridge_entry.barCode,
                                   date_in=date_in_iso,
                                   cartridge_id=cartridge_entry.cartridge_id,
                                   builddep_id=cartridge_entry.builddep_id,
                                   description=cartridge_entry.description,
                                   status_id=cartridge_entry.status_id,
                                   cartridges=cartridges,
                                   departments=departments)

        except Exception as e:
            logging.error(f"Ошибка при получении данных: {e}")
            return f"Произошла ошибка: {e}"
        finally:
            db.close()
    else:
        old_barcode = request.form.get('oldBarcode')  
        new_barcode = request.form.get('barCode')
        
        if not new_barcode or not old_barcode:
            return "Неверные данные", 400

        db = SessionLocal()
        try:
            if new_barcode != old_barcode:
                existing_entry = db.query(CartridgeEntry).filter(
                    CartridgeEntry.barCode == new_barcode
                ).first()
                if existing_entry:
                    return f"Штрих-код {new_barcode} уже существует!", 400

            if new_barcode == old_barcode:
                cartridge_entry = db.query(CartridgeEntry).filter(
                    CartridgeEntry.barCode == old_barcode
                ).first()
                cartridge_entry.cartridge_id = int(request.form.get('cartridgeSelect'))
                cartridge_entry.description = request.form.get('newDescription')
                cartridge_entry.date_in = datetime.strptime(
                    request.form.get('date_in'), 
                    '%Y-%m-%dT%H:%M'
                )
                cartridge_entry.builddep_id = int(request.form.get('departmentSelect'))
                cartridge_entry.status_id = int(request.form.get('statusSelect'))
            else:
                new_cartridge_entry = CartridgeEntry(
                    barCode=new_barcode,
                    cartridge_id=int(request.form.get('cartridgeSelect')),
                    description=request.form.get('newDescription'),
                    date_in=datetime.strptime(
                        request.form.get('date_in'), 
                        '%Y-%m-%dT%H:%M'
                    ),
                    builddep_id=int(request.form.get('departmentSelect')),
                    status_id=int(request.form.get('statusSelect'))
                )
                db.add(new_cartridge_entry)
                dependent_services = db.query(Service).filter(
                    Service.barCode == old_barcode
                ).all()
                for service in dependent_services:
                    service.barCode = new_barcode

            db.commit()
            return redirect(url_for('cartridges', barcode=new_barcode if new_barcode != old_barcode else old_barcode))

        except ValueError as e:
            db.rollback()
            logging.error(f"Ошибка формата данных: {e}")
            return f"Неверный формат данных: {e}", 400
        except Exception as e:
            db.rollback()
            logging.error(f"Ошибка при обновлении: {e}")
            return f"Ошибка: {str(e)}", 500
        finally:
            db.close()



@app.route('/api/departments')
def get_departments():
    db = SessionLocal()
    try:
        departments = db.query(Department).all()
        return jsonify([{"department_id": d.department_id, "name": d.name} for d in departments])
    finally:
        db.close()

@app.route('/api/building_departments')
def get_building_departments():
    db = SessionLocal()
    try:
        building_departments = db.query(BuildingDepartment).all()
        result = []
        for bd in building_departments:
            department_name = bd.department.name
            building_name = bd.building.name
            result.append({
                "builddep_id": bd.builddep_id,
                "name": f"{building_name} - {department_name}"
            })
        return jsonify(result)
    finally:
        db.close()

def check_cartridge_id(db, cartridge_id):
    existing_cartridge = db.query(Cartridge).filter(Cartridge.cartridge_id == cartridge_id).first()
    return existing_cartridge is not None

@app.route('/api/update_cartridge', methods=['POST'])
def update_cartridge():
    barcode = request.form.get('barCode')
    date_in = request.form.get('date_in')
    cartridge_id = request.form.get('cartridgeSelect')
    department_id = request.form.get('departmentSelect')
    status_id = request.form.get('statusSelect')
    description = request.form.get('newDescription')

    db = SessionLocal()
    try:
        cartridge_entry = db.query(CartridgeEntry).filter(CartridgeEntry.barCode == barcode).first()
        if not cartridge_entry:
            return jsonify({"error": "Картридж не найден"}), 404

        if cartridge_id and not check_cartridge_id(db, int(cartridge_id)):
            return jsonify({"error": f"Cartridge_id {cartridge_id} не найден в таблице cartridges."}), 400

        if status_id not in ['3', '4', '5']:
            return jsonify({"error": "Недопустимый статус"}), 400

        if date_in:
            cartridge_entry.date_in = datetime.strptime(date_in, '%Y-%m-%dT%H:%M')
        cartridge_entry.cartridge_id = int(cartridge_id) if cartridge_id else cartridge_entry.cartridge_id
        cartridge_entry.builddep_id = int(department_id) if department_id else cartridge_entry.builddep_id
        cartridge_entry.status_id = int(status_id)
        cartridge_entry.description = description if description else cartridge_entry.description

        db.commit()

        return jsonify({"message": "Информация о картридже успешно обновлена."}), 200

    except ValueError as ve:
        print(f"ValueError: {ve}")
        db.rollback()
        return jsonify({"error": f"Неверный формат данных: {str(ve)}"}), 400
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        db.rollback()
        return jsonify({"error": f"Произошла непредвиденная ошибка: {str(e)}"}), 500
    finally:
        db.close()

@app.route('/service')
def service():
    return render_template('service.html')

@app.route('/api/cartridge_list_by_department')
def get_cartridge_list_by_department():
    db = SessionLocal()
    try:
        departments = db.query(Department).all()

        department_list = []
        for department in departments:
            building_departments = db.query(BuildingDepartment).filter(BuildingDepartment.department_id == department.department_id).all()
            department_data = {
                "department_id": department.department_id,
                "department_name": department.name,
                "cartridges": []
            }
            for bd in building_departments:
                cartridge_entries = db.query(CartridgeEntry).filter(CartridgeEntry.builddep_id == bd.builddep_id).all()
                for entry in cartridge_entries:
                    cartridge = entry.cartridge
                    if cartridge:
                        department_data["cartridges"].append({
                            "barCode": entry.barCode,
                            "model_name": cartridge.model.name if cartridge.model else "Нет данных",
                            "manufacturer_name": cartridge.manufacturer.name if cartridge.manufacturer else "Нет данных",
                            "description": entry.description,
                            "date_in": str(entry.date_in)
                        })
            department_list.append(department_data)

        return jsonify(department_list)
    finally:
        db.close()

@app.route('/create_cartridge', methods=['GET', 'POST'])
def create_cartridge():
    db = SessionLocal()
    try:
        if request.method == 'POST':
            new_entry = CartridgeEntry(
                barCode=request.form['barcode'],
                cartridge_id=request.form['cartridge_id'],
                description=request.form['description'],
                date_in=datetime.strptime(request.form['date_in'], '%Y-%m-%d'),
                builddep_id=request.form['builddep_id'],
                status_id=request.form['status_id']
            )
            
            db.add(new_entry)
            db.commit()
            return redirect(url_for('service'))
        
        departments = db.query(BuildingDepartment).all()
        statuses = db.query(Status).filter(Status.status_id.in_([3, 4, 5])).all()
        cartridges = db.query(Cartridge).options(joinedload(Cartridge.model)).all()
        
        return render_template('create_cartridge.html', 
                            departments=departments,
                            statuses=statuses,
                            cartridges=cartridges)
    
    except Exception as e:
        db.rollback()
        logging.error(f"Ошибка при создании картриджа: {e}")
        return f"Ошибка: {str(e)}"
    finally:
        db.close()

@app.route('/department_cartridges', methods=['GET'])
def department_cartridges():
    db = SessionLocal()
    try:
        departments = db.query(BuildingDepartment).options(
            joinedload(BuildingDepartment.building),
            joinedload(BuildingDepartment.department)
        ).all()

        department_name = request.args.get('department_name')
        selected_department = None
        cartridges_info = []

        if department_name:
            selected_department = db.query(BuildingDepartment).join(
                BuildingDepartment.department
            ).filter(
                Department.name.ilike(f"%{department_name}%")
            ).first()

        if selected_department:
            selected_department_name = f"{selected_department.building.name} - {selected_department.department.name}"
            
            cartridges = db.query(CartridgeEntry).filter(
                CartridgeEntry.builddep_id == selected_department.builddep_id
            ).all()

            cartridges.sort(key=lambda x: x.status_id != 4)
            for cartridge in cartridges:
                cartridge_status = db.query(Status).filter(Status.status_id == cartridge.status_id).first()
                status_name = cartridge_status.name if cartridge_status else "Нет данных"
                
                service = db.query(Service).filter(Service.barCode == cartridge.barCode).order_by(Service.date_in.desc()).first()
                if service:
                    if service.date_get:
                        location = "У сотрудника"
                    elif service.date_recieve:
                        location = "На складе после СЦ"
                    elif service.date_out:
                        location = "В СЦ"
                    else:
                        location = "На складе"
                else:
                    location = "На складе"
                
                cartridges_info.append({
                    'barCode': cartridge.barCode,
                    'cartridge_name': cartridge.cartridge.model.name if cartridge.cartridge else "Нет данных",
                    'description': cartridge.description,
                    'status': status_name,
                    'location': location
                })

        return render_template(
            'department_cartridges.html',
            departments=departments,
            selected_department=selected_department_name if selected_department else None,
            cartridges=cartridges_info
        )

    except Exception as e:
        print(f"Ошибка: {str(e)}")
        return f"Ошибка сервера: {str(e)}", 500

    finally:
        db.close()

@app.route('/api/cartridges_by_department', methods=['GET'])
def cartridges_by_department():
    db = SessionLocal()
    try:
        department_id = request.args.get('department_id')

        query = db.query(
            Cartridge.model_id,
            Model.name.label('model_name'),
            func.count(CartridgeEntry.barCode).label('cartridge_count')
        ).join(CartridgeEntry, Cartridge.cartridge_id == CartridgeEntry.cartridge_id)\
         .join(Model, Cartridge.model_id == Model.model_id)\
         .join(BuildingDepartment, CartridgeEntry.builddep_id == BuildingDepartment.builddep_id)

        if department_id:
            query = query.filter(BuildingDepartment.builddep_id == int(department_id))

        query = query.group_by(Cartridge.model_id, Model.name).all()

        result = []
        for row in query:
            result.append({
                'model': row.model_name,
                'count': row.cartridge_count
            })

        return jsonify(result)
    except Exception as e:
        print(f"Ошибка: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@app.route('/service/storage_all', methods=['GET'])
def storage_all():
    db = SessionLocal()
    try:
        departments = db.query(BuildingDepartment).options(
            joinedload(BuildingDepartment.building),
            joinedload(BuildingDepartment.department)
        ).all()

        cartridges_info = []

        for department in departments:
            department_name = f"{department.building.name} - {department.department.name}"

            cartridges = db.query(CartridgeEntry).filter(
                CartridgeEntry.builddep_id == department.builddep_id
            ).options(
                joinedload(CartridgeEntry.cartridge).joinedload(Cartridge.model)
            ).all()

            if cartridges:
                models_dict = {}
                for cartridge in cartridges:
                    if cartridge.cartridge and cartridge.cartridge.model:
                        model_name = cartridge.cartridge.model.name
                        if model_name in models_dict:
                            models_dict[model_name]['count'] += 1
                        else:
                            models_dict[model_name] = {'count': 1}
                    else:
                        pass

                department_cartridges = []
                for model_name, model_info in models_dict.items():
                    department_cartridges.append({
                        'model': model_name,
                        'count': model_info['count']
                    })

                cartridges_info.append({
                    'department': department_name,
                    'cartridges': department_cartridges,
                    'builddep_id': department.builddep_id
                })
            else:
                print(f"Нет картриджей для отделения: {department_name}")
                cartridges_info.append({
                    'department': department_name,
                    'cartridges': [{'model': 'Нет данных', 'count': 0}],
                    'builddep_id': department.builddep_id
                })

        return render_template(
            'storage_all.html',
            departments=departments,
            cartridges=cartridges_info
        )

    except Exception as e:
        print(f"Ошибка: {str(e)}")
        return f"Ошибка сервера: {str(e)}", 500

    finally:
        db.close()

@app.route('/service/used_in_warehouse')
def used_in_warehouse():
    db = SessionLocal()
    try:
        barcode = request.args.get('barcode')
        
        if barcode:
            used_cartridges = db.query(CartridgeEntry).filter(
                CartridgeEntry.status_id == 5, CartridgeEntry.barCode.like(f'%{barcode}%')
            ).all()
        else:
            used_cartridges = db.query(CartridgeEntry).filter(
                CartridgeEntry.status_id == 5
            ).all()

        cartridges_with_details = []
        for cartridge_entry in used_cartridges:
            department_info = "Нет данных"
            if cartridge_entry.builddep_id:
                building_department = db.query(BuildingDepartment).filter(
                    BuildingDepartment.builddep_id == cartridge_entry.builddep_id
                ).first()
                if building_department:
                    department_info = f"{building_department.building.name} - {building_department.department.name}"

            model_name = cartridge_entry.cartridge.model.name if cartridge_entry.cartridge and cartridge_entry.cartridge.model else "Нет модели"

            cartridges_with_details.append({
                'barCode': cartridge_entry.barCode,
                'description': cartridge_entry.description,
                'model': model_name,
                'department': department_info
            })

        return render_template('used_in_warehouse.html', cartridges=cartridges_with_details)
    except Exception as e:
        logging.error(f"Ошибка при рендеринге шаблона used_in_warehouse.html: {e}")
        return f"Произошла ошибка при рендеринге страницы: {e}"
    finally:
        db.close()


def check_cartridge_id(db, cartridge_id):
    existing_cartridge = db.query(Cartridge).filter(Cartridge.cartridge_id == cartridge_id).first()
    return existing_cartridge is not None

if __name__ == '__main__':
    Base.metadata.create_all(engine)
    print("open http://127.0.0.1:5000/")
    app.run(debug=False)
