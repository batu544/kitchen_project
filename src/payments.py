from flask import Blueprint, request, render_template, jsonify
import db_config as db

from psycopg2.extensions import cursor as crs

payment_bp = Blueprint("payments", __name__, url_prefix="/payment")


@payment_bp.route("/", methods=["GET"])
def get_payment():
    print("We are in Payments blueprint")
    return "We are in Payment BluePrint"


@payment_bp.route("/record_pay", methods=["PUT"])
def record_payment():
    print("We are in record payment PUT")
    message = ""
    order_id = request.args.get("order_id")
    # validate the entered data
    if order_id.isnumeric():
        print("Entered order id :", order_id)
        cursor, conn = db.db_connect()
        try:
            cursor.execute(
                "UPDATE kitch_payment_dtl "
                "SET kpd_total_payable_amount = kpd_payment_amount, "
                "kpd_amount_paid = kpd_payment_amount, "
                "kpd_payment_status = 'paid', "
                "kpd_payment_dt = current_date "
                "where kpd_order_id = %s",
                (order_id,),
            )
            if cursor.rowcount > 0:
                order_header_count = mark_orders_paid(cursor, order_id)
                if order_header_count:
                    message = f"Payment for order id {order_id} updated successfully!"
            else:
                message = "No Payments updated. Please contact support!"
            db.close_connection(cursor, conn)
        except Exception as e:
            print("Database error encountered: ", e)
            message = f"Database error encountered: {e}"
    else:
        message = "Invalid order id passed"

    return jsonify({"message": message})


def mark_orders_paid(cur: crs, orderid: str) -> str:
    # update order item table as delivered
    cur.execute("UPDATE kitch_order_details "
                "SET kod_order_status = 'delivered' "
                ", kod_order_lst_updt_tms = current_timestamp "
                "where kod_order_internal_id = ( select ko_order_internal_id from kitch_orders "
                " where ko_order_id = %s ) "
                "and kod_order_status not in ('cancelled')"
                , (orderid,))

    cur.execute("update kitch_orders "
                "set ko_order_status = 'paid' "
                ", ko_order_lst_updt_tms = CURRENT_TIMESTAMP "
                "where ko_order_id = %s ",(orderid, ))

    return cur.rowcount
