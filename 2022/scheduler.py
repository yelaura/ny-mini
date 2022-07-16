import schedule
import time
import day1

schedule.every(15).minutes.do(day1.day1)

while True:
    schedule.run_pending()
    time.sleep(1)