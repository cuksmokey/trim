import sqlite3
import numpy as np
import os
import json
import pandas as pd
from datetime import datetime
import multiprocessing
import threading
from flask import Flask, request, jsonify, render_template_string
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from parallel_trimming import run_parallel_trimming, process_substance
from trimming_state import trimming_state
import atexit

app = Flask(__name__, static_folder='static', static_url_path='/static')

HOME_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Trimming System</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/react/18.2.0/umd/react.production.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/react-dom/18.2.0/umd/react-dom.production.min.js"></script>
    <script src="/static/UnpairedRollsSuggestions.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 0 auto; max-width: 1200px; padding: 20px; }
        h1, h2 { color: #333; }
        .data-section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        table { width: 100%; border-collapse: collapse; margin: 10px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f5f5f5; }
        form { margin-bottom: 20px; }
        label { display: inline-block; width: 100px; }
        input[type="number"] { width: 100px; }
        input[type="submit"] { margin-top: 10px; padding: 5px 15px; }
        .info { color: #666; margin: 5px 0; }
        .error { color: red; }
        .success { color: green; }
    </style>
</head>
<body>
    <div style="text-align: right; margin: 10px;">
        <a href="/backlog" style="padding: 8px 15px; background-color: #007bff; color: white; text-decoration: none; border-radius: 4px;">
            View Operation Backlog
        </a>
    </div>
    
    <h1>Trimming System</h1>

    <div class="data-section">
    <h2>Current Orders and Trimming Plans by Substance</h2>
    {% for substance in substances %}
    <div class="substance-section" style="margin-bottom: 30px; border-bottom: 2px solid #eee; padding-bottom: 20px;">
        <h3>{{ substance.name }}</h3>

        <!-- Orders Table -->
        <h4>Current Orders</h4>
        <table>
            <tr>
                <th>Width (Ukuran)</th>
                <th>Quantity</th>
            </tr>
            {% for order in orders_by_substance[substance.id] %}
            <tr>
                <td>{{ order[1] }}</td>
                <td>{{ order[2] }}</td>
            </tr>
            {% endfor %}
        </table>

        <!-- Trimming Plan for this substance -->
        <h4>Trimming Plan</h4>
        <div class="info">
            <p>Total Weight of Unpaired Rolls: {{ trimming_plans[substance.id].weight_final }} tonnes</p>
            <p>Number of Pairs in PM1: {{ trimming_plans[substance.id].cut_1_final }}</p>
        </div>

        <!-- Trim Details -->
        <h4>Trim Composition Details:</h4>
        <table>
            <tr>
                <th>Width 1</th>
                <th>Quantity 1</th>
                <th>Width 2</th>
                <th>Quantity 2</th>
                <th>Width 3</th>
                <th>Quantity 3</th>
            </tr>
            {% for detail in trimming_plans[substance.id].trim_details %}
            <tr>
                <td>{{ detail[0] }}</td>
                <td>{{ detail[1] | int }}</td>
                <td>{{ detail[2] }}</td>
                <td>{{ detail[3] | int }}</td>
                <td>{{ detail[4] if detail[4] else '-' }}</td>
                <td>{{ detail[5] | int if detail[5] else '-' }}</td>
            </tr>
            {% endfor %}
        </table>

        <!-- Remaining Rolls -->
        <h4>Remaining Unpaired Rolls and Suggestions:</h4>
        <div class="grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div>
                <h5 style="margin-bottom: 10px; font-weight: 500;">Current Unpaired Rolls</h5>
                <table>
                    <tr>
                        <th>Width</th>
                        <th>Quantity</th>
                    </tr>
                    {% for remaining in trimming_plans[substance.id].remaining_rolls %}
                    <tr>
                        <td>{{ remaining[0] }}</td>
                        <td>{{ remaining[2] }}</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
            <div id="suggestions-{{ substance.id }}"></div>
        </div>

        <script>
        (function() {
            const rolls = {{ trimming_plans[substance.id].remaining_rolls | tojson | safe }};
            const container = document.getElementById('suggestions-{{ substance.id }}');
            if (rolls && rolls.length > 0) {
                ReactDOM.render(
                    React.createElement(window.UnpairedRollsSuggestions, {
                        remainingRolls: rolls,
                        maxWidth: 312
                    }),
                    container
                );
            }
        })();
    </script>
    </div>
    {% endfor %}
    </div> 

    <div class="data-section">
    <h2>Add New Order</h2>
    <form action="/new_order" method="post" id="new-order-form">
        <label>Substance:
            <select name="substance_id" required>
                {% for substance in substances %}
                <option value="{{ substance.id }}">{{ substance.name }}</option>
                {% endfor %}
            </select>
        </label><br><br>

        <div id="order-entries">
            <div class="order-entry" style="display: grid; grid-template-columns: 200px 200px; gap: 10px; margin-bottom: 10px;">
                <div>
                    <label>Width:</label>
                    <input type="number" name="ukuran[]" placeholder="Width">
                </div>
                <div>
                    <label>Quantity:</label>
                    <input type="number" name="quantity[]" placeholder="Quantity">
                </div>
            </div>
        </div>

        <button type="button" onclick="addNewEntry()" style="margin-right: 10px;">Add More Entries</button>
        <input type="submit" value="Submit All Orders">
    </form>
    <div id="new-order-message"></div>
    </div>

    <div class="data-section">
    <h2>Update Production</h2>
    <form action="/production_update" method="post" id="production-form">
        <label>Substance:
            <select name="substance_id" required>
                {% for substance in substances %}
                <option value="{{ substance.id }}">{{ substance.name }}</option>
                {% endfor %}
            </select>
        </label><br>
        <label>Width 1: <input type="number" name="ukuran1" required></label><br>
        <label>Width 2: <input type="number" name="ukuran2" required></label><br>
        <label>Width 3: <input type="number" name="ukuran3"></label><br>
        <label>Quantity: <input type="number" name="quantity" required></label><br>
        <input type="submit" value="Update Production">
    </form>
    <div id="production-message"></div>
    </div>

    <div class="info">
        <p>Last updated: {{ last_update }}</p>
        <p>Next update in: {{ next_update }} minutes</p>
    </div>

    <script>
    function addNewEntry() {
        const container = document.getElementById('order-entries');
        const newEntry = document.createElement('div');
        newEntry.className = 'order-entry';
        newEntry.style = 'display: grid; grid-template-columns: 200px 200px; gap: 10px; margin-bottom: 10px;';

        newEntry.innerHTML = `
            <div>
                <label>Width:</label>
                <input type="number" name="ukuran[]" placeholder="Width">
            </div>
            <div>
                <label>Quantity:</label>
                <input type="number" name="quantity[]" placeholder="Quantity">
            </div>
        `;

        container.appendChild(newEntry);
    }

    // Add 10 empty entries by default when page loads
    document.addEventListener('DOMContentLoaded', function() {
        for (let i = 0; i < 9; i++) { // Add 9 more to the 1 that's already there
            addNewEntry();
        }
    });

    document.querySelector('#new-order-form').onsubmit = async (e) => {
        e.preventDefault();
        
        // Gather all non-empty entries
        const entries = [];
        const substance_id = e.target.querySelector('select[name="substance_id"]').value;
        const ukurans = e.target.querySelectorAll('input[name="ukuran[]"]');
        const quantities = e.target.querySelectorAll('input[name="quantity[]"]');
        
        for (let i = 0; i < ukurans.length; i++) {
            if (ukurans[i].value && quantities[i].value) {
                entries.push({
                    ukuran: parseInt(ukurans[i].value),
                    quantity: parseInt(quantities[i].value)
                });
            }
        }
    
        if (entries.length === 0) {
            const messageDiv = document.querySelector('#new-order-message');
            messageDiv.innerHTML = `<p class="error">Please enter at least one order</p>`;
            return;
        }
    
        const requestData = {
            substance_id: parseInt(substance_id),
            orders: entries
        };
        
        console.log('Sending data:', requestData);  // Debug log
        
        // Send only non-empty entries
        try {
            const response = await fetch('/new_order', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(requestData)
            });
            
            // Debug logs
            console.log('Response status:', response.status);
            const responseText = await response.text();
            console.log('Response text:', responseText);
            
            let result;
            try {
                result = JSON.parse(responseText);
            } catch (e) {
                throw new Error(`Invalid JSON response: ${responseText}`);
            }
            
            const messageDiv = document.querySelector('#new-order-message');
            
            if (response.ok) {
                messageDiv.innerHTML = `<p class="success">${result.message}</p>`;
                setTimeout(() => location.reload(), 1500);
            } else {
                messageDiv.innerHTML = `<p class="error">Error: ${result.message}</p>`;
            }
        } catch (error) {
            console.error('Error:', error);  // Debug log
            const messageDiv = document.querySelector('#new-order-message');
            messageDiv.innerHTML = `<p class="error">Error submitting orders: ${error}</p>`;
        }
    };

    document.querySelector('#production-form').onsubmit = async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const response = await fetch('/production_update', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();

        const messageDiv = document.querySelector('#production-message');
        if (response.ok) {
            messageDiv.innerHTML = `<p class="success">${result.message}</p>`;
            setTimeout(() => location.reload(), 1500);
        } else {
            messageDiv.innerHTML = `<p class="error">Error: ${result.message}</p>`;
        }
    };
    </script>
</body>
</html>
"""


def create_tables():
    """Create database tables with optimizations"""
    conn = sqlite3.connect('trimming_system.db')
    c = conn.cursor()

    # Create substances table
    c.execute('''CREATE TABLE IF NOT EXISTS substances
                 (id INTEGER PRIMARY KEY,
                  name TEXT UNIQUE,
                  description TEXT)''')

    # Create orders table with better indexing
    c.execute('''CREATE TABLE IF NOT EXISTS orders
                 (id INTEGER PRIMARY KEY, 
                  ukuran INTEGER, 
                  quantity INTEGER,
                  substance_id INTEGER,
                  FOREIGN KEY (substance_id) REFERENCES substances(id))''')

    # Create indexes for better performance
    c.execute('''CREATE INDEX IF NOT EXISTS idx_orders_substance_ukuran 
                 ON orders(substance_id, ukuran)''')

    # Create trimming_plan table
    c.execute('''CREATE TABLE IF NOT EXISTS trimming_plan
                 (id INTEGER PRIMARY KEY, 
                  substance_id INTEGER,
                  ukuran_finaltrim_sisaorder TEXT,
                  weight_final REAL,
                  detail_trim_PM1_PM2 TEXT,
                  cut_1_final INTEGER,
                  FOREIGN KEY (substance_id) REFERENCES substances(id))''')

    c.execute('''CREATE INDEX IF NOT EXISTS idx_trimming_plan_substance 
                 ON trimming_plan(substance_id)''')

    # Create operation_backlog table
    c.execute('''CREATE TABLE IF NOT EXISTS operation_backlog
                 (id INTEGER PRIMARY KEY,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                  operation_type TEXT,
                  substance_name TEXT,
                  details TEXT,
                  user_action TEXT)''')

    # Insert default substances
    default_substances = [
        ('WP65', '65 gsm wrapping paper'),
        ('WP68', '68 gsm wrapping paper'),
        ('WP70', '70 gsm wrapping paper'),
        ('ML110', '110 gsm medium liner paper'),
        ('ML125', '125 gsm medium liner paper'),
        ('ML150', '150 gsm medium liner paper'),
        ('ML200', '200 gsm medium liner paper'),
        ('MD110', '110 gsm medium paper'),
        ('MD125', '125 gsm medium paper'),
        ('MD150', '150 gsm medium paper'),
        ('MD200', '200 gsm medium paper'),
        ('BK110', '110 gsm kraft paper'),
        ('BK125', '125 gsm kraft paper'),
        ('BK150', '150 gsm kraft paper'),
        ('BK200', '200 gsm kraft paper'),
    ]

    c.executemany("INSERT OR IGNORE INTO substances (name, description) VALUES (?, ?)",
                  default_substances)

    conn.commit()
    conn.close()
    print("Database tables created/updated successfully.")

def get_current_orders_state():
    """Get current state of all orders grouped by substance"""
    conn = sqlite3.connect('trimming_system.db')
    c = conn.cursor()
    try:
        c.execute("SELECT id, name FROM substances ORDER BY name")
        substances = c.fetchall()

        orders_state = {}
        for substance_id, substance_name in substances:
            c.execute("""
                SELECT ukuran, quantity 
                FROM orders 
                WHERE substance_id = ? 
                ORDER BY ukuran ASC
            """, (substance_id,))
            substance_orders = c.fetchall()

            if substance_orders:
                orders_state[substance_name] = [
                    {"width": order[0], "quantity": order[1]}
                    for order in substance_orders
                ]

        return orders_state
    finally:
        conn.close()

def log_operation(operation_type, substance_name, details, user_action):
    """Log operations to database and file with current state"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    current_orders = get_current_orders_state()

    # Database logging
    conn = sqlite3.connect('trimming_system.db')
    try:
        c = conn.cursor()
        c.execute("""
            INSERT INTO operation_backlog 
            (operation_type, substance_name, details, user_action) 
            VALUES (?, ?, ?, ?)
        """, (operation_type, substance_name, details, user_action))
        conn.commit()
    except Exception as e:
        print(f"Error logging to database: {e}")
        conn.rollback()
    finally:
        conn.close()

    # File logging
    log_dir = "operation_logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    month_year = datetime.now().strftime("%Y_%m")
    log_file = os.path.join(log_dir, f"operations_{month_year}.txt")

    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"""
================================================
Timestamp: {timestamp}
Operation: {operation_type}
Substance: {substance_name}
Details: {details}
Action: {user_action}

Current Orders State:
{json.dumps(current_orders, indent=2)}
================================================\n
""")
    except Exception as e:
        print(f"Error logging to file: {e}")


@app.route('/')
def home():
    conn = sqlite3.connect('trimming_system.db')
    c = conn.cursor()

    try:
        # Get all substances
        c.execute("""
            SELECT id, name, description 
            FROM substances 
            ORDER BY name
        """)
        substances = [{"id": row[0], "name": row[1]} for row in c.fetchall()]

        # Get orders by substance
        orders_by_substance = {}
        for substance in substances:
            c.execute("""
                SELECT * FROM orders 
                WHERE substance_id = ?
                ORDER BY ukuran ASC
            """, (substance["id"],))
            orders_by_substance[substance["id"]] = c.fetchall()

        # Get trimming plans
        trimming_plans = {}
        current_time = datetime.now()

        for substance in substances:
            c.execute("""
                SELECT * FROM trimming_plan 
                WHERE substance_id = ?
            """, (substance["id"],))
            plan = c.fetchone()

            if plan:
                try:
                    ukuran_finaltrim = np.array(json.loads(plan[2]) if plan[2] else [])
                    trim_details = np.array(json.loads(plan[4]) if plan[4] else [])

                    remaining_rolls = []
                    if len(ukuran_finaltrim) > 0:
                        mask = ukuran_finaltrim[:, 5] > 0
                        remaining = ukuran_finaltrim[mask]

                        if len(remaining) > 0:
                            remaining = remaining[remaining[:, 0].argsort()]
                            for row in remaining:
                                if row[5] > 0:
                                    remaining_rolls.append([
                                        int(row[0]),
                                        int(row[4]),
                                        int(row[5])
                                    ])

                    trimming_plans[substance["id"]] = {
                        "weight_final": float(plan[3]) if plan[3] is not None else 0.0,
                        "cut_1_final": int(plan[5]) if plan[5] is not None else 0,
                        "trim_details": trim_details,
                        "remaining_rolls": remaining_rolls
                    }
                except Exception as e:
                    print(f"Error processing plan for substance {substance['id']}: {e}")
                    trimming_plans[substance["id"]] = {
                        "weight_final": 0,
                        "cut_1_final": 0,
                        "trim_details": [],
                        "remaining_rolls": []
                    }
            else:
                trimming_plans[substance["id"]] = {
                    "weight_final": 0,
                    "cut_1_final": 0,
                    "trim_details": [],
                    "remaining_rolls": []
                }

        current_minute = current_time.minute
        next_update = 60 - current_minute if current_minute < 60 else 0

        return render_template_string(
            HOME_TEMPLATE,
            substances=substances,
            orders_by_substance=orders_by_substance,
            trimming_plans=trimming_plans,
            last_update=current_time.strftime("%Y-%m-%d %H:%M:%S"),
            next_update=next_update
        )

    except Exception as e:
        print(f"Error in home route: {e}")
        return render_template_string(
            HOME_TEMPLATE,
            substances=[],
            orders_by_substance={},
            trimming_plans={},
            last_update="Error",
            next_update="Unknown"
        )
    finally:
        conn.close()


@app.route('/new_order', methods=['POST'])
def new_order():
    try:
        if not request.is_json:
            return jsonify({"status": "error", "message": "Content-Type must be application/json"}), 400

        data = request.get_json()
        substance_id = data.get('substance_id')
        orders = data.get('orders', [])

        if not substance_id:
            return jsonify({"status": "error", "message": "Substance must be specified"}), 400

        if not orders:
            return jsonify({"status": "error", "message": "No orders provided"}), 400

        # Stop any current processing for this substance
        trimming_state.stop_processing(substance_id)

        with sqlite3.connect('trimming_system.db', timeout=30) as conn:
            c = conn.cursor()

            try:
                # Verify substance exists
                c.execute("SELECT name FROM substances WHERE id = ?", (substance_id,))
                substance = c.fetchone()
                if not substance:
                    return jsonify({"status": "error", "message": "Invalid substance ID"}), 400

                # Process orders in transaction
                for order in orders:
                    ukuran = int(order['ukuran'])
                    quantity = int(order['quantity'])

                    c.execute("""
                        SELECT quantity 
                        FROM orders 
                        WHERE ukuran = ? AND substance_id = ?
                    """, (ukuran, substance_id))
                    existing = c.fetchone()

                    if existing:
                        c.execute("""
                            UPDATE orders 
                            SET quantity = quantity + ? 
                            WHERE ukuran = ? AND substance_id = ?
                        """, (quantity, ukuran, substance_id))
                    else:
                        c.execute("""
                            INSERT INTO orders (ukuran, quantity, substance_id) 
                            VALUES (?, ?, ?)
                        """, (ukuran, quantity, substance_id))

                conn.commit()

                # Log operation
                details = json.dumps({'orders': orders}, indent=2)
                log_operation('New Order', substance[0], details, f"Added {len(orders)} new orders")

                # Start new calculation in background
                thread = threading.Thread(
                    target=process_substance,
                    args=(substance_id,)
                )
                thread.daemon = True
                thread.start()

                return jsonify({
                    "status": "success",
                    "message": "Orders added successfully and calculation started"
                }), 201

            except Exception as e:
                conn.rollback()
                return jsonify({
                    "status": "error",
                    "message": f"Database error: {str(e)}"
                }), 500

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Request processing error: {str(e)}"
        }), 500


@app.route('/production_update', methods=['POST'])
def production_update():
    try:
        substance_id = request.form.get('substance_id', type=int)
        ukuran1 = request.form.get('ukuran1', type=int)
        ukuran2 = request.form.get('ukuran2', type=int)
        ukuran3 = request.form.get('ukuran3', type=int)
        quantity = request.form.get('quantity', type=int)

        if not all([substance_id, ukuran1, ukuran2, quantity]):
            return jsonify({
                "status": "error",
                "message": "Missing required fields"
            }), 400

        # Stop any current processing for this substance
        trimming_state.stop_processing(substance_id)

        with sqlite3.connect('trimming_system.db', timeout=30) as conn:
            c = conn.cursor()

            try:
                c.execute("SELECT name FROM substances WHERE id = ?", (substance_id,))
                substance = c.fetchone()
                if not substance:
                    return jsonify({
                        "status": "error",
                        "message": "Invalid substance ID"
                    }), 400

                # Verify quantities
                widths = [(ukuran1, "Width 1"), (ukuran2, "Width 2")]
                if ukuran3:
                    widths.append((ukuran3, "Width 3"))

                for width, name in widths:
                    c.execute("""
                        SELECT quantity 
                        FROM orders 
                        WHERE ukuran = ? AND substance_id = ?
                    """, (width, substance_id))
                    result = c.fetchone()

                    if not result:
                        return jsonify({
                            "status": "error",
                            "message": f"{name} not found in orders"
                        }), 400

                    if result[0] < quantity:
                        return jsonify({
                            "status": "error",
                            "message": f"Insufficient quantity for {name}"
                        }), 400

                # Update quantities
                for width in [w for w, _ in widths]:
                    c.execute("""
                        UPDATE orders 
                        SET quantity = quantity - ? 
                        WHERE ukuran = ? AND substance_id = ?
                    """, (quantity, width, substance_id))

                # Remove zero quantity orders
                c.execute("""
                    DELETE FROM orders 
                    WHERE quantity <= 0 AND substance_id = ?
                """, (substance_id,))

                conn.commit()

                # Log operation
                details = json.dumps({
                    'widths': [w for w, _ in widths],
                    'quantity': quantity
                }, indent=2)
                log_operation('Production Update', substance[0], details,
                              f"Updated production quantities for {len(widths)} widths")

                # Start new calculation in background
                thread = threading.Thread(
                    target=process_substance,
                    args=(substance_id,)
                )
                thread.daemon = True
                thread.start()

                return jsonify({
                    "status": "success",
                    "message": "Production updated successfully and calculation started"
                }), 200

            except Exception as e:
                conn.rollback()
                return jsonify({
                    "status": "error",
                    "message": f"Database error: {str(e)}"
                }), 500

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Request processing error: {str(e)}"
        }), 500


def export_data_to_excel():
    """Export current database state to Excel file"""
    try:
        # Create directory for exports if it doesn't exist
        export_dir = "data_exports"
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)

        # Generate timestamp for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_file = os.path.join(export_dir, f"trimming_system_export_{timestamp}.xlsx")

        # Connect to database
        conn = sqlite3.connect('trimming_system.db')

        # Create Excel writer object
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            # Export substances
            df_substances = pd.read_sql_query("SELECT * FROM substances ORDER BY name", conn)
            df_substances.to_excel(writer, sheet_name='Substances', index=False)

            # Export orders with substance names
            orders_query = """
                SELECT 
                    o.id,
                    s.name as substance_name,
                    o.ukuran,
                    o.quantity,
                    o.substance_id
                FROM orders o
                JOIN substances s ON s.id = o.substance_id
                ORDER BY s.name, o.ukuran
            """
            df_orders = pd.read_sql_query(orders_query, conn)
            df_orders.to_excel(writer, sheet_name='Orders', index=False)

            # Export trimming plans with substance names
            plans_query = """
                SELECT 
                    tp.id,
                    s.name as substance_name,
                    tp.weight_final,
                    tp.cut_1_final,
                    tp.substance_id,
                    tp.ukuran_finaltrim_sisaorder,
                    tp.detail_trim_PM1_PM2
                FROM trimming_plan tp
                JOIN substances s ON s.id = tp.substance_id
                ORDER BY s.name
            """
            df_plans = pd.read_sql_query(plans_query, conn)

            # Convert JSON strings to more readable format
            def parse_trim_details(json_str):
                if pd.isna(json_str):
                    return ""
                try:
                    data = json.loads(json_str)
                    return str(data)
                except:
                    return str(json_str)

            df_plans['ukuran_finaltrim_sisaorder'] = df_plans['ukuran_finaltrim_sisaorder'].apply(parse_trim_details)
            df_plans['detail_trim_PM1_PM2'] = df_plans['detail_trim_PM1_PM2'].apply(parse_trim_details)

            df_plans.to_excel(writer, sheet_name='Trimming_Plans', index=False)

            # Set column widths
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for idx, col in enumerate(worksheet.columns, 1):
                    max_length = 0
                    column = worksheet.column_dimensions[chr(64 + idx)]  # A, B, C, ...

                    # Find the maximum length in the column
                    for cell in col:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass

                    adjusted_width = (max_length + 2)
                    column.width = min(adjusted_width, 50)  # Cap width at 50

        print(f"Data exported successfully to {excel_file}")
        return excel_file

    except Exception as e:
        print(f"Error exporting data to Excel: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()


def periodic_update():
    """Handler for scheduled periodic updates"""
    try:
        print("\n" + "=" * 50)
        print(f"Starting periodic update at {datetime.now()}")

        # Stop all current processing
        trimming_state.stop_all_processing()

        # Run parallel trimming
        run_parallel_trimming()

        # Export data to Excel
        exported_file = export_data_to_excel()
        if exported_file:
            print(f"Data exported to: {exported_file}")

        # Mark periodic update as complete
        trimming_state.finish_periodic_update()

        print(f"Completed periodic update at {datetime.now()}")
        print("=" * 50 + "\n")
    except Exception as e:
        print(f"Error in periodic update: {e}")
        trimming_state.finish_periodic_update()


if __name__ == '__main__':
    # Required for Windows to avoid recursive imports
    multiprocessing.freeze_support()

    if not os.path.exists('trimming_system.db'):
        # Only create new database if it doesn't exist
        create_tables()
        print("New database created successfully.")
    else:
        print("Using existing database.")

    # Initial run
    run_parallel_trimming()

    # Set up scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=periodic_update,
        trigger=CronTrigger(minute='1'),
        id='periodic_trimming',
        max_instances=1,
        coalesce=True
    )

    scheduler.start()
    print(f"Scheduler started successfully.")

    # Register shutdown handler
    atexit.register(lambda: scheduler.shutdown())

    # Run in production mode
    app.run(debug=False, host='0.0.0.0', port=5000)