import time
from screener import run_screener

def main():
    while True:
        print("🔁 Running 15-minute auto scan...")
        run_screener()
        time.sleep(900)  # 15 minutes

if __name__ == "__main__":
    main()