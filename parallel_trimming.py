import multiprocessing
import sqlite3
import numpy as np
import json
from datetime import datetime
from trimming_random import trimming_random
from trimming_state import trimming_state


def store_trimming_results(conn, substance_id, result):
    """Store trimming calculation results in database"""
    c = conn.cursor()

    ukuran_finaltrim_json = json.dumps(result[0].tolist())
    detail_trim_json = json.dumps(result[2].tolist() if result[2] is not None else [])

    c.execute("DELETE FROM trimming_plan WHERE substance_id = ?", (substance_id,))

    c.execute("""
        INSERT INTO trimming_plan 
        (substance_id, ukuran_finaltrim_sisaorder, weight_final, 
         detail_trim_PM1_PM2, cut_1_final)
        VALUES (?, ?, ?, ?, ?)
    """, (
        substance_id,
        ukuran_finaltrim_json,
        float(result[1]),
        detail_trim_json,
        int(result[3])
    ))
    conn.commit()


def process_substance(substance_id):
    """Process a single substance with interrupt handling"""
    print(f"Starting calculation for substance {substance_id} at {datetime.now()}")

    # Mark substance as being processed
    trimming_state.start_processing(substance_id)

    conn = sqlite3.connect('trimming_system.db')

    try:
        c = conn.cursor()

        # Get orders for this substance
        c.execute("""
            SELECT ukuran, quantity 
            FROM orders 
            WHERE substance_id = ?
            ORDER BY ukuran ASC
        """, (substance_id,))
        orders = c.fetchall()

        if not orders:
            print(f"No orders to process for substance {substance_id}")
            return

        ukuran = np.array([order[0] for order in orders])
        order = np.array([order[1] for order in orders])
        lebar_1, lebar_2, lebar_3 = 312, 312, 312

        # Run calculation with substance_id for interrupt checking
        result = trimming_random(order, ukuran, lebar_1, lebar_2, lebar_3, substance_id)

        if result[0] is not None:
            store_trimming_results(conn, substance_id, result)
            print(f"Calculation completed for substance {substance_id} at {datetime.now()}")

    except Exception as e:
        print(f"Error processing substance {substance_id}: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
        # Clear processing state
        trimming_state.stop_processing(substance_id)


def run_parallel_trimming():
    """Run trimming calculations for all substances in parallel"""
    conn = sqlite3.connect('trimming_system.db')
    c = conn.cursor()

    try:
        # Get all substances with orders
        c.execute("""
            SELECT DISTINCT s.id
            FROM substances s
            INNER JOIN orders o ON s.id = o.substance_id
            ORDER BY s.name
        """)
        substances = [row[0] for row in c.fetchall()]

        if not substances:
            print("No substances to process")
            return

        # Create a pool of workers
        num_processes = min(len(substances), multiprocessing.cpu_count())
        print(f"Starting parallel processing with {num_processes} processes")

        # Create and start processes
        with multiprocessing.Pool(processes=num_processes) as pool:
            pool.map(process_substance, substances)

        print("All substance calculations completed")

    except Exception as e:
        print(f"Error in parallel trimming: {e}")
    finally:
        conn.close()


if __name__ == '__main__':
    run_parallel_trimming()