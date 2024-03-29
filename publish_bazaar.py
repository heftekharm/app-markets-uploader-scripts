import requests
import json

GENERATED_APK_PATH = "app.apk"
CAFE_BAZAAR_API_KEY = "API_KEY"
print("Make sure there is no in-progress release on CafeBazaar")
# Create release request
release_response = requests.post(
    "https://api.pishkhan.cafebazaar.ir/v1/apps/releases/",
    headers={"CAFEBAZAAR-PISHKHAN-API-SECRET": CAFE_BAZAAR_API_KEY},
)

if release_response.status_code == 201:
    print("Release request is successful")

    # Create package upload request
    package_upload_response = requests.post(
        "https://api.pishkhan.cafebazaar.ir/v1/apps/releases/upload/",
        headers={"CAFEBAZAAR-PISHKHAN-API-SECRET": CAFE_BAZAAR_API_KEY},
        files={"apk": open(GENERATED_APK_PATH, "rb")},
        params={"architecture": "all"},
    )

    if package_upload_response.status_code in [200, 201]:
        print("Package successfully uploaded")

        # Read changelists
        changeListFa = open("Market_Changelist_Fa.txt", "r" , encoding = "utf8").read()
        changeListEn = open("Market_Changelist_En.txt", "r" , encoding = "utf8").read()

        # Construct JSON payload for rollout request
        rollout_payload = {
            "changelog_en": changeListEn,
            "changelog_fa": changeListFa,
            "developer_note": "",
            "staged_rollout_percentage": 10,
            "auto_publish": False,
        }

        rollout_response = requests.post(
            "https://api.pishkhan.cafebazaar.ir/v1/apps/releases/commit/",
            headers={
                "CAFEBAZAAR-PISHKHAN-API-SECRET": CAFE_BAZAAR_API_KEY,
                "Content-Type": "application/json"
            },
            data=json.dumps(rollout_payload))
        print("Rollout status code is", rollout_response.status_code)