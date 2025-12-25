import os
import glob

SCRAPED_RESULTS_DIR = os.path.join(os.path.dirname(__file__), 'scraped_results')

def delete_all_scraped_results():
    files = glob.glob(os.path.join(SCRAPED_RESULTS_DIR, 'scraped_*.csv'))
    deleted = 0
    for file_path in files:
        try:
            os.remove(file_path)
            deleted += 1
        except Exception as e:
            print(f"Failed to delete {file_path}: {e}")
    print(f"Deleted {deleted} scraped result file(s).")

if __name__ == "__main__":
    delete_all_scraped_results()
