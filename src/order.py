from typing import Any

from flask import Blueprint, render_template, request, jsonify
import db_config as db
import datetime

order_bp = Blueprint(
    "order", "__name__", url_prefix="/order"
)  # Use Blueprint for modular routing


@order_bp.route("/", methods=["GET"])
def orders():
    """
    get latest 10 orders of current date.
    """
    print("We are in order page GET !!")
    cursor, conn = db.db_connect()
    cursor.execute(
        "select ko_order_id, to_char(ko_order_dt, 'yyyy-mm-dd') as ko_order_dt, kcd_cust_name, "
        "ko_order_total, ko_order_status from kitch_orders, kitch_customer_dtl "
        "where ko_customer_id = kcd_cust_id "
        "order by ko_order_dt desc , ko_order_id desc limit 10"
    )
    order_items = cursor.fetchall()

    db.close_connection(cursor, conn)
    return render_template("order_tracking.html", orderItems=order_items)


@order_bp.route("/new_order", methods=["GET"])
def new_order():
    print("We are in new order GET")
    return render_template("new_order.html", title="New Order")


@order_bp.route("/new_order", methods=["POST"])
def create_order():
    print("We are in Order creation form POST")
    name = request.form.get("customer_name")
    number = request.form.get("customer_number").replace("-", "")
    cust_id = check_customer(name, number)

    item_name = request.form.getlist("order_item[]")
    qty = request.form.getlist("qty[]")
    price = request.form.getlist("price[]")
    spicy = request.form.getlist("spicy_level[]")
    internal_id = datetime.datetime.now()
    order_dt = datetime.datetime.now().strftime("%Y-%m-%d")

    updated_price = get_price(item_name, price)

    order_lines = [
        (
            str(internal_id),
            item,
            qty,
            "box",
            float(price) * float(qty),
            "ordered",
            "ONLNUSR",
        )
        for (item, price), qty, spicy in zip(updated_price, qty, spicy)
    ]

    cursor, conn = db.db_connect()

    cursor.executemany(
        "INSERT INTO kitch_order_details (kod_order_internal_id, kod_order_item_name, kod_order_qty, "
        "kod_order_unit, kod_order_price, kod_order_status, kod_order_lst_updt_usr) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        order_lines,
    )

    # save the other summary in KITCH_ORDERS table
    total_amount = sum([order[4] for order in order_lines])
    data = (
        str(internal_id),
        order_dt,
        len(order_lines),
        cust_id,
        total_amount,
        "ordered",
        "ONLNUSR",
    )

    cursor.execute(
        "INSERT INTO kitch_orders (ko_order_internal_id, ko_order_dt, ko_total_items, ko_customer_id"
        ", ko_order_total, ko_order_status, ko_order_lst_updt_usr) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING ko_order_id ",
        data,
    )
    order_id = cursor.fetchone()
    # Make an entry in payment detail table with order id and total amount
    cursor.execute("INSERT INTO kitch_payment_dtl (kpd_order_id, kpd_payment_amount, kpd_payment_status, "
                   "kpd_payment_dt, kpd_lst_updt_usr) "
                   " values (%s, %s, %s, %s, %s) ", (order_id, total_amount, 'pending', '9999-01-01', 'ONLNUSR'))

    conn.commit()

    if order_id:
        print("Order saver successfully, Here is your order id: {}".format(order_id[0]))

    db.close_connection(cursor, conn)

    return jsonify({"message": order_id[0]})


def check_customer(name, number):
    """
    takes name and phone as input and checks customer table if phone number already exist.
    If present, then returns customer id. If present and name is different, then update the name and returns id
    If not present, then insert a new record and returns the customer id.
    """
    cursor, conn = db.db_connect()
    cursor.execute(
        "select kcd_cust_id, kcd_cust_name, kcd_cust_number "
        "from kitch_customer_dtl "
        "where kcd_cust_number = %s",
        (number,),
    )
    customers = cursor.fetchone()
    if customers:
        if customers[1] != name:
            cursor.execute(
                "UPDATE kitch_customer_dtl "
                "set kcd_cust_name = %s "
                ", kcd_cust_lst_updt_tms = CURRENT_TIMESTAMP "
                ", kcd_cust_lst_updt_usr = %s "
                "where kcd_cust_id = %s",
                (name, "ORDRSCRN", customers[0]),
            )
            cust_id = customers[0]
        else:
            cust_id = customers[0]
    else:
        # insert new customer and return the cust_id
        cursor.execute(
            "INSERT INTO kitch_customer_dtl "
            "(kcd_cust_name, kcd_cust_number, kcd_cust_lst_updt_usr ) "
            "VALUES ( %s, %s, %s) "
            "RETURNING kcd_cust_id",
            (name, number, "ORDRSCRN"),
        )
        cust_id = cursor.fetchone()[0]

    conn.commit()
    db.close_connection(cursor, conn)
    return cust_id


def get_price(item_name: list, amount: list):
    """
    get the price for provided input items from kitch_item_catalg table
    """
    item_price = zip(item_name, amount)
    updated_price = []
    cursor, conn = db.db_connect()
    for item, price in item_price:
        query = (
            "SELECT kic_name, kic_price "
            "FROM kitch_item_catalg "
            "WHERE lower(kic_name) = %s"
        )
        cursor.execute(query, (item.lower(),))
        price_from_table = cursor.fetchone()
        if price_from_table:
            price = price_from_table[1]
        updated_price.append((item, price))
    return updated_price


@order_bp.route("/view_order", methods=["GET"])
def view_orders():
    return render_template("view_order.html", title="View Order")
    # return "View/edit other page"


@order_bp.route("/search_orders", methods=["GET"])
def search_order():
    """
    search the existing orders by provided criteria and return in json format
    """
    print(dict(request.args.items()))
    order_id = request.args.get("order_id")
    customer_name = request.args.get("customer_name").strip()
    customer_number = request.args.get("customer_number")
    order_dt = request.args.get("order_date")
    if order_dt == "":
        order_dt = "1999-01-01"

    cursor, conn = db.db_connect()

    if order_id:
        cursor.execute(
            "SELECT ko_order_id, ko_order_dt::char(10), kcd_cust_name, kcd_cust_number, ko_total_items, "
            "ko_order_total::float, ko_order_status "
            "from kitch_orders, kitch_customer_dtl "
            "where ko_customer_id = kcd_cust_id and ko_order_id = %s",
            (order_id,),
        )
        order_summary = cursor.fetchone()
        if order_summary:
            data = [
                {
                    "order_id": order_summary[0],
                    "order_date": order_summary[1],
                    "customer_name": order_summary[2],
                    "customer_number": order_summary[3],
                    "total_items": order_summary[4],
                    "total_amount": order_summary[5],
                    "order_status": order_summary[6],
                }
            ]
            return jsonify({"orders": data})
    else:
        cursor.execute(
            "select ko_order_id, ko_order_dt::char(10), kcd_cust_name, kcd_cust_number, ko_total_items, "
            "ko_order_total::float, ko_order_status "
            "from kitch_orders, kitch_customer_dtl "
            "where ko_customer_id = kcd_cust_id "
            "and ( %s = '' or kcd_cust_name ilike %s) "
            "and (%s < '' or ko_order_dt > %s ) "
            "and (%s = '' or kcd_cust_number = %s)"
            "order by ko_order_id desc",
            (
                customer_name,
                f"%{customer_name}%",
                order_dt,
                order_dt,
                customer_number,
                customer_number,
            ),
        )
        order_summary = cursor.fetchall()
        if order_summary:
            data = [
                {
                    "order_id": orders_d[0],
                    "order_date": orders_d[1],
                    "customer_name": orders_d[2],
                    "customer_number": orders_d[3],
                    "total_items": orders_d[4],
                    "total_amount": orders_d[5],
                    "order_status": orders_d[6],
                }
                for orders_d in order_summary
            ]
            print(data)
            db.close_connection(cursor, conn)
            return jsonify({"orders": data})
    db.close_connection(cursor, conn)
    return {"orders": ""}


@order_bp.route("/edit_order", methods=["GET"])
def edit_view_order():
    """
    get the order details from order details table and display it in a new template
    """
    order_id = request.args.get("order_id")
    print("we are in edit order GET with order id : {}".format(order_id))
    cursor, conn = db.db_connect()
    try:
        cursor.execute(
            "select ko_order_id, kcd_cust_name, "
            "kcd_cust_number, "
            "ko_total_items, "
            "ko_order_total::float, "
            "ko_order_status "
            "from kitch_orders a "
            ", kitch_customer_dtl b "
            "where ko_customer_id = kcd_cust_id  "
            " and ko_order_id = %s",
            (order_id,),
        )
        order_header: Any = cursor.fetchone()
        if order_header:
            cursor.execute(
                "select kod_order_item_name, kod_order_qty, "
                "kod_order_unit, kod_order_price, kod_order_status "
                "from kitch_order_details a "
                ", kitch_orders b "
                "where kod_order_internal_id = ko_order_internal_id "
                "and ko_order_id = %s",
                (order_id,),
            )
            order_lines = cursor.fetchall()
            if order_lines:
                output = [
                    {
                        "item_name": order_line[0],
                        "order_qty": order_line[1],
                        "order_unit": order_line[2],
                        "order_price": order_line[3],
                        "order_status": order_line[4],
                    }
                    for order_line in order_lines
                ]
        else:
            return {"message": "No orders found"}
    except Exception as e:
        print("Error occurred: {}".format(e))

    return_data = {
        "message": "success",
        "order_header": order_header,
        "order_lines": output,
    }
    print(return_data)

    db.close_connection(cursor, conn)

    return render_template("edit_order.html", returnData=return_data)


@order_bp.route("/edit_order/<int:order_id>", methods=["PUT"])
def edit_order(order_id):
    """
    edit the order after validating the new fields.
    return: return success message after edit done
    """
    # get the order items from table.
    cursor, conn = db.db_connect()
    # cursor.execute("select a.kod_order_item_name, a.kod_order_qty::varchar(10) "
    #                ",a.kod_order_unit, a.kod_order_price::varchar(10), a.kod_order_status "
    #                "from kitch_order_details a"
    #                ", kitch_orders b"
    #                " where kod_order_internal_id = ko_order_internal_id "
    #                " and ko_order_id = %s", (order_id,))
    # order_lines = cursor.fetchall()
    # old_order_lines = [{"item_name": order_line[0], "order_qty": order_line[1], "order_unit": order_line[2],
    #                     "order_price": order_line[3], "order_status": order_line[4]}
    #                    for order_line in order_lines]
    #
    # print(f"data from table: ", old_order_lines)
    cursor.execute(
        "select ko_order_internal_id:: varchar(26) "
        "from kitch_orders "
        "where ko_order_id = %s",
        (order_id,),
    )
    ord_internal_id = cursor.fetchone()[0]
    print("ord_internal_id", ord_internal_id)

    # clear all entries from order details table
    try:
        cursor.execute(
            "DELETE FROM kitch_order_details " "where kod_order_internal_id = %s",
            (ord_internal_id,),
        )
    except Exception as e:
        print("Error occured: ", e)

    # data received from the front end

    new_order_lines: list = request.json.get("order_lines", [])

    item_name = [order["item_name"] for order in new_order_lines]
    price = [order["order_price"] for order in new_order_lines]
    order_status = []
    qty = []
    for order in new_order_lines:
        order_status.append(order["order_status"])
        qty.append(order["order_qty"])

    updated_price = get_price(item_name, price)
    print(updated_price)

    formated_order_lines = [
        (
            str(ord_internal_id),
            item,
            qty,
            "box",
            float(price) * float(qty),
            status,
            "ONLNUSR",
        )
        for (item, price), qty, status in zip(updated_price, qty, order_status)
    ]

    print("formated_order_lines", formated_order_lines)
    cursor.executemany(
        "INSERT INTO kitch_order_details (kod_order_internal_id, kod_order_item_name, kod_order_qty, "
        "kod_order_unit, kod_order_price, kod_order_status, kod_order_lst_updt_usr) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        formated_order_lines,
    )

    total_amount = sum([order[4] for order in formated_order_lines])

    # update order header record with new amount

    cursor.execute(
        "UPDATE kitch_orders SET ko_total_items = %s  "
        ",ko_order_total = %s "
        ",ko_order_lst_updt_tms = CURRENT_TIMESTAMP "
        " WHERE ko_order_id = %s",
        (
            len(formated_order_lines),
            total_amount,
            order_id,
        ),
    )

    db.close_connection(cursor, conn)
    return {"status": "success", "message": "We reached in PUT"}


@order_bp.route("/view_order/<int:order_id>", methods=["DELETE"])
def cancel_order(order_id):
    """
    Order cancellation routine
    """
    cursor, conn = db.db_connect()
    try:
        cursor.execute(
            "UPDATE kitch_orders "
            "SET ko_order_status = 'cancelled' "
            "WHERE ko_order_id = %s",
            (order_id,),
        )
        cursor.execute(
            "UPDATE kitch_order_details "
            "SET kod_order_status = 'cancelled' "
            "where kod_order_internal_id in "
            "( select distinct ko_order_internal_id from kitch_orders "
            "where ko_order_id = %s )",
            (order_id,),
        )
    except Exception as e:
        print("Database error encountered: ", e)

    db.close_connection(cursor, conn)
    return jsonify({"message": "Successfully Cancelled the Order!"})
