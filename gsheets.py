from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import Optional
import os
import re


load_dotenv()
GOOGLE_SHEETS_API_KEY = os.getenv("GOOGLE_SHEETS_API_KEY")
GOOGLE_SPREADSHEET_ID = os.getenv("GOOGLE_SPREADSHEET_ID")
GOOGLE_SPREADSHEET_RANGE = os.getenv("GOOGLE_SPREADSHEET_RANGE")


class KvK:
    def __init__(self) -> None:
        self.data = self._get_from_google_sheets()
        self.last_idx_fields_date = None
        self.last_fields_headers = None
        self.governors = None

        if len(self.data) > 0:
            first_row = self.data[0]
            idx_fields_dates = [
                i for i, h in enumerate(first_row) if re.search("^\d+/\d+/\d+$", h)
            ]
            len_idx_fields_dates = len(idx_fields_dates)
            if len_idx_fields_dates > 0:
                self.last_idx_fields_date = idx_fields_dates[len_idx_fields_dates - 1]
                self.last_fields_headers = first_row[self.last_idx_fields_date :]

            self.data_sorted = sorted(
                self.data[1:],
                key=lambda gov: int(gov[len(gov) - 1].replace(",", "")),
                reverse=True,
            )

            total_governors = len(self.data_sorted)

            self.governors = {
                r[0]: r + [f"{i+1}/{total_governors}"]
                for i, r in enumerate(self.data_sorted)
                if len(r) > 0
            }

    def get_last_registered_date(self) -> Optional[str]:
        if self.last_fields_headers is None:
            return None
        return self.last_fields_headers[0]

    def get_governor_last_data(self, gov_id: int) -> Optional[dict]:
        if self.last_idx_fields_date is None or self.governors is None:
            return None
        gov_id_str = str(gov_id)
        governor = self.governors.get(gov_id_str, None)
        if governor is None:
            return
        headers = (
            ["ID", "BASE NAME", "BASE POWER", "BASE KILL POINTS"]
            + self.last_fields_headers[1:]
            + ["KVK RANK"]
        )
        governor = governor[0:4] + governor[self.last_idx_fields_date + 1 :]
        return dict(zip(headers, governor))

    def get_top_governors(self, top=300):
        if not self.data_sorted or len(self.data_sorted) == 0:
            return []

        top = min(top, len(self.data_sorted))

        valid_governors = []

        for g in self.data_sorted:
            if len(g) > 17 and g[17-1] and g[16-1]:
                try:
                    score = int(g[17-1].replace(",", ""))
                    goal = int(g[16-1].replace(",", ""))
                    valid_governors.append(g)
                except ValueError:
                    continue

        valid_governors.sort(key=lambda g: int(g[17-1].replace(",", "")), reverse=True)

        return list(
            map(
                lambda g: dict(
                    id=g[0],
                    name=g[1],
                    score=int(g[17-1].replace(",", "")),
                    goal=int(g[16-1].replace(",", "")),
                    rate=g[17]
                ),
                valid_governors[:top]
            )
        )

    def _get_from_google_sheets(self) -> []:
        try:
            service = build("sheets", "v4", developerKey=GOOGLE_SHEETS_API_KEY)
            sheet = service.spreadsheets()
            result = (
                sheet.values()
                .get(
                    spreadsheetId=GOOGLE_SPREADSHEET_ID, range=GOOGLE_SPREADSHEET_RANGE
                )
                .execute()
            )
            values = result.get("values", [])
            if not values:
                print("No data found.")
                service.close()
                return []
            service.close()
            return values
        except HttpError as err:
            print(err)
            return []


def main():
    kvk = KvK()
    print(kvk.last_fields_headers)
    print(kvk.get_last_registered_date())
    print(kvk.get_governor_last_data(132799325))
    print(kvk.get_top_governors(top=10))


if __name__ == "__main__":
    main()
