import os
from flask import Flask, render_template, request, jsonify, session
from flask_mysqldb import MySQL
from datetime import datetime
import html
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.environ.get('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD', 'password')
app.config['MYSQL_DB'] = os.environ.get('MYSQL_DB', 'message_app')
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

def init_db():
    """Initialize the database and create tables if they don't exist"""
    try:
        with app.app_context():
            cur = mysql.connection.cursor()
            cur.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                user_id VARCHAR(50) DEFAULT 'anonymous'
            );
            ''')
            mysql.connection.commit()
            cur.close()
            print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")
        print("Please check your MySQL connection settings in the .env file")
        
with app.app_context():
    try:
        init_db()
    except Exception as e:
        print(f"Failed to initialize database on startup: {e}")
        print("Database will be initialized when first accessed")

@app.before_request
def make_session_permanent():
    session.permanent = True
    if 'user_id' not in session:
        session['user_id'] = os.urandom(16).hex()

@app.route('/')
def index():
    try:
        try:
            init_db()
        except:
            pass  
            
        cur = mysql.connection.cursor()
        cur.execute('SELECT id, message, created_at, user_id FROM messages ORDER BY created_at DESC')
        messages = cur.fetchall()
        cur.close()
        return render_template('index.html', messages=messages, user_id=session['user_id'])
    except Exception as e:
        print(f"Database error: {e}")
        return render_template('index.html', messages=[], user_id=session['user_id'], db_error=str(e))

@app.route('/submit', methods=['POST'])
def submit():
    try:
        new_message = request.form.get('new_message', '').strip()
        if not new_message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        safe_message = html.escape(new_message)
        user_id = session.get('user_id', 'anonymous')
        
        cur = mysql.connection.cursor()
        cur.execute('INSERT INTO messages (message, user_id) VALUES (%s, %s)', (safe_message, user_id))
        mysql.connection.commit()

        cur.execute('SELECT id, message, created_at FROM messages WHERE id = %s', (cur.lastrowid,))
        new_msg = cur.fetchone()
        cur.close()
        
        return jsonify({
            'id': new_msg['id'],
            'message': new_msg['message'],
            'created_at': new_msg['created_at'].strftime('%b %d, %Y %I:%M %p'),
            'user_id': user_id,
            'is_owner': True
        })
    except Exception as e:
        print(f"Error submitting message: {e}")
        return jsonify({'error': 'Database error: Unable to save message. Please check your connection.'}), 500

@app.route('/delete/<int:message_id>', methods=['DELETE'])
def delete_message(message_id):
    try:
        user_id = session.get('user_id')
        cur = mysql.connection.cursor()
        cur.execute('SELECT user_id FROM messages WHERE id = %s', (message_id,))
        message = cur.fetchone()
        
        if not message:
            return jsonify({'error': 'Message not found'}), 404
            
        if message['user_id'] != user_id:
            return jsonify({'error': 'Not authorized to delete this message'}), 403
            
        cur.execute('DELETE FROM messages WHERE id = %s', (message_id,))
        mysql.connection.commit()
        cur.close()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error deleting message: {e}")
        return jsonify({'error': 'Database error: Unable to delete message.'}), 500

@app.route('/edit/<int:message_id>', methods=['PUT'])
def edit_message(message_id):
    try:
        data = request.get_json()
        new_message = data.get('message', '').strip()
        
        if not new_message:
            return jsonify({'error': 'Message cannot be empty'}), 400
            
        user_id = session.get('user_id')
        safe_message = html.escape(new_message)
        
        cur = mysql.connection.cursor()
        
        cur.execute('SELECT user_id FROM messages WHERE id = %s', (message_id,))
        message = cur.fetchone()
        
        if not message:
            return jsonify({'error': 'Message not found'}), 404
            
        if message['user_id'] != user_id:
            return jsonify({'error': 'Not authorized to edit this message'}), 403
            
        cur.execute('UPDATE messages SET message = %s WHERE id = %s', (safe_message, message_id))
        mysql.connection.commit()
        
        cur.execute('SELECT id, message, created_at, updated_at FROM messages WHERE id = %s', (message_id,))
        updated_msg = cur.fetchone()
        cur.close()
        
        return jsonify({
            'id': updated_msg['id'],
            'message': updated_msg['message'],
            'updated_at': updated_msg['updated_at'].strftime('%b %d, %Y %I:%M %p')
        })
    except Exception as e:
        print(f"Error editing message: {e}")
        return jsonify({'error': 'Database error: Unable to edit message.'}), 500

@app.route('/health')
def health_check():
    """Endpoint to check database connection status"""
    try:
        cur = mysql.connection.cursor()
        cur.execute('SELECT 1')
        cur.close()
        return jsonify({'status': 'healthy', 'database': 'connected'})
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'database': 'disconnected', 'error': str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)