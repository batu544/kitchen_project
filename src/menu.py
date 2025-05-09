from flask import Blueprint, render_template, jsonify, request
import db_config as db

menu_bp = Blueprint(
    "menu", __name__, url_prefix="/menu"
)  # Use Blueprint for modular routing


# Get all menu items
@menu_bp.route("/", methods=["GET"])
def get_menu():
    print("We are in menu GET !!")
    cursor, conn = db.db_connect()
    cursor.execute(
        "select a.kic_id, b.kc_cat_name, initcap(a.kic_name), a.kic_price, "
        "case when a.kic_party_flag = 'Y' then TO_CHAR(ROUND(a.kic_price*4*.96), '9999.99') else 'Not "
        "Available' end as small_tray,"
        "case when a.kic_party_flag = 'Y' then TO_CHAR(ROUND(a.kic_price*6*.96), '9999.99') else 'Not "
        "Available' end as med_tray,"
        "case when a.kic_party_flag = 'Y' then TO_CHAR(ROUND(a.kic_price*11*.91), '9999.99') else 'Not "
        "Available' end as large_tray ,"
        "a.kic_cd, a.kic_party_flag "
        "from kitch_item_catalg a, kitch_category b "
        "where a.kic_cd = b.kc_cd "
        "order by kc_cat_name, kic_cd desc, initcap(kic_name);"
    )
    menu_items = cursor.fetchall()
    db.close_connection(cursor, conn)
    return render_template("menu.html", menuItems=menu_items)


# Delete a menu item
@menu_bp.route("/<int:id>", methods=["DELETE"])
def delete_menu_item(id):
    cursor, conn = db.db_connect()
    cursor.execute("DELETE FROM kitch_item_catalg WHERE kic_id = %s", (id,))
    conn.commit()
    db.close_connection(cursor, conn)
    return jsonify({"message": "Item deleted successfully!"})


# Add a new menu item
@menu_bp.route("/", methods=["POST"])
def add_menu_item():
    cursor, conn = db.db_connect()
    data = request.json
    print(data)
    kic_name = data["name"]
    kic_cd = data["category"]
    kic_price = data["price"]
    kic_part_flag = data["partyFlag"]
    try:
        cursor.execute(
            "INSERT INTO kitch_item_catalg "
            "(kic_cd, kic_name, kic_price, kic_party_flag) "
            "VALUES (%s, %s, %s, %s)",
            (kic_cd, kic_name, kic_price, kic_part_flag),
        )
        conn.commit()
        return jsonify({"message": "Item added successfully!"})
    except Exception as e:
        print("Error occurred:", e)
        conn.rollback()
    finally:
        db.close_connection(cursor, conn)


# Edit a menu item
@menu_bp.route("/<int:id>", methods=["PUT"])
def edit_menu_item(id):
    data = request.json
    name = data["name"]
    kic_cd = data["category"]
    price = data["price"]
    partyflag = data["partyFlag"]

    cursor, conn = db.db_connect()
    # check the old value before updating
    cursor.execute(
        "SELECT kic_cd, kic_name, kic_price::int::varchar(10), kic_party_flag "
        "FROM kitch_item_catalg "
        "WHERE kic_id = %s",
        (id,),
    )
    row = cursor.fetchone()

    print(row)
    test = (kic_cd, name, price, partyflag)
    print(test)
    if row == (kic_cd, name, price, partyflag):
        db.close_connection(cursor, conn)
        print("No update done!!!")
        return jsonify({"message": "No change detected. No updates made!"})
    else:
        cursor.execute(
            "UPDATE kitch_item_catalg SET kic_name = %s, kic_cd = %s, kic_price = %s , kic_party_flag = %s "
            ", kic_lst_updt_tms = CURRENT_TIMESTAMP , kic_lst_updt_usr = 'ONLINE'"
            "WHERE kic_id = %s ",
            (name, kic_cd, price, partyflag, id),
        )
        conn.commit()

    db.close_connection(cursor, conn)
    return jsonify({"message": "Menu item updated successfully!"})
