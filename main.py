from app import app

def main():
    # Optimized for fast navigation - no WebSockets, no background processes
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    main()
