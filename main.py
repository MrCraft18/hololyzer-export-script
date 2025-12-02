import csv
import os
import requests
import re
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup

HOLODEX_API_KEY = os.getenv("HOLODEX_API_KEY")
if not HOLODEX_API_KEY:
    raise ValueError("HOLODEX_API_KEY not found in environment variables")

hololyzer_url = "https://hololyzer.net"
holodex_api_url = "https://holodex.net/api/v2"

response_string_en = requests.get(hololyzer_url + "/youtube/locales/string_en.json")
response_string_en.raise_for_status()
response_string_en.encoding = "utf-8"
string_en = response_string_en.json()

response_string_ja = requests.get(hololyzer_url + "/youtube/locales/string_ja.json")
response_string_ja.raise_for_status()
response_string_ja.encoding = "utf-8"
string_ja = response_string_ja.json()

def channels():
    response = requests.get(hololyzer_url)
    response.raise_for_status()
    response.encoding = "utf-8"

    soup = BeautifulSoup(response.text, 'html.parser')
    
    channel_labels = soup.find_all(attrs={"data-i18n": "label.sidemenu.list"})
    channels = []

    for channel_label in channel_labels:
        id = channel_label.parent.get('href').split('/')[-1].replace('.html', '')

        channel_parent = channel_label.find_parent('details')
        label_name = channel_parent.select_one('[data-i18n^="label.name."]').get('data-i18n').split('.')[-1]
        en_name = string_en['label']['name'].get(label_name, channel_parent.find('summary').text)
        ja_name = string_ja['label']['name'].get(label_name, channel_parent.find('summary').text)

        category_parent = channel_parent.find_parent('details')
        label_category = category_parent.select_one('[data-i18n^="label.category."]').get('data-i18n').split('.')[-1]
        en_category = string_en['label']['category'].get(label_category, category_parent.find('summary').text)
        ja_category = string_ja['label']['category'].get(label_category, category_parent.find('summary').text)

        # channels.append(Channel(id, en_name, ja_name, en_category, ja_category))

        channels.append({
            "id": id,
            "en_name": en_name,
            "ja_name": ja_name,
            "en_category": en_category,
            "ja_category": ja_category
        })

    return channels

def get_video_data(video_id):
    data = {
        'video_id': video_id,

        'public_time': None,
        'start_time': None,
        'end_time': None,

        'total_time': None,

        'chat_num_total': None,
        'chat_num_ja': None,
        'chat_num_emoji': None,
        'chat_num_en': None,

        'uniq_user_num': None,
        'uniq_member_num': None,

        'total_super_chat_amount_yen': None,

        'english_chat_ratio': None,
        'member_chat_ratio': None,

        'chat_per_second': None,

        'max_ccv': None,

        'member_num': None,

        'member_gift_num_from': None,
        'member_gift_num_to': None,

        'milestone_num': None
    }

    try:
        response = requests.get(f"{hololyzer_url}/youtube/video/{video_id}.html")
        response.raise_for_status()

    except requests.exceptions.HTTPError as error:
        if error.response is not None and error.response.status_code != 404: raise
        return data
    else:
        response.encoding = "utf-8"

        soup = BeautifulSoup(response.text, 'html.parser')

        table = soup.select_one('table[height]')

        if not table: raise

        table_text = table.get_text()

        table_text = table_text.replace("\r\n", "\n").strip("\n")
        lines = [line.replace('　', '').strip() for line in table_text.split('\n') if '：' in line]

        # for line in lines: print(line)

        # return

        def extract_field(field_type, line):
            if '-' not in line:
                field = line.split('：')[1]

                if field_type == 'date':
                    string_no_timezone = field.replace("(JST)", "")

                    if not string_no_timezone: return None

                    dt_naive = datetime.strptime(string_no_timezone.strip(), "%Y/%m/%d %H:%M:%S")

                    jst = timezone(timedelta(hours=9))
                    dt_jst = dt_naive.replace(tzinfo=jst)

                    return dt_jst
                elif field_type == 'string':
                    return field if field else None
                elif field_type == 'int':
                    match = re.search(r"\d+", field.replace(',', ''))
                    return int(match.group()) if match else None
                elif field_type == 'percent':
                    match = re.search(r"[\d\.]+", field.replace(',', ''))
                    return float(match.group()) / 100 if match else None
                elif field_type == 'float':
                    match = re.search(r"[\d\.]+", field.replace(',', ''))
                    return float(match.group()) if match else None
            else: return None

        for line in lines:
            if line.startswith('公開日時'): data['public_time'] = extract_field('date', line)
            if line.startswith('開始日時'): data['start_time'] = extract_field('date', line)
            if line.startswith('終了日時'): data['end_time'] = extract_field('date', line)

            if line.startswith('動画時間'): data['total_time'] = extract_field('string', line)

            if line.startswith('総チャット数'): data['chat_num_total'] = extract_field('int', line)
            if line.startswith('チャット数（日本語）'): data['chat_num_ja'] = extract_field('int', line)
            if line.startswith('チャット数（スタンプ）'): data['chat_num_emoji'] = extract_field('int', line)
            if line.startswith('チャット数（英語）'): data['chat_num_en'] = extract_field('int', line)

            if line.startswith('ユニークユーザー数'): data['uniq_user_num'] = extract_field('int', line)
            if line.startswith('ユニークメンバー数'): data['uniq_member_num'] = extract_field('int', line)

            if line.startswith('総スパチャ金額'): data['total_super_chat_amount_yen'] = extract_field('int', line)

            if line.startswith('英語コメ率'): data['english_chat_ratio'] = extract_field('percent', line)
            if line.startswith('メンバーコメ率'): data['member_chat_ratio'] = extract_field('percent', line)

            if line.startswith('平均毎秒コメ数'): data['chat_per_second'] = extract_field('float', line)

            if line.startswith('最大同接'): data['max_ccv'] = extract_field('int', line)

            if line.startswith('メンシ入り'): data['member_num'] = extract_field('int', line)

            if line.startswith('メンシギフト') and '-' not in line:
                match = re.search(r"(\d+)\D+(\d+)", line)

                if match:
                    data['member_gift_num_from'] = int(match.group(1))
                    data['member_gift_num_to'] = int(match.group(2))

            if line.startswith('マイルストーン'): data['milestone_num'] = extract_field('int', line)

        # print(data)

        return data


def videos_with_data(channel, csv_writer, fieldnames, existing_ids=None):
    """Fetch video ids for channel, stream each video's data into csv_writer.

    csv_writer is expected to be a csv.DictWriter already configured with fieldnames.
    """
    video_ids = []

    print(f"Fetching video ids from Holodex for channel", channel['en_name'], channel['id'])
    while (True):
        params = {
            "type": "stream",
            "limit": 50,
            "offset": len(video_ids)
        }

        headers = { "X-APIKEY": HOLODEX_API_KEY }

        response = requests.get(f"{holodex_api_url}/channels/{channel['id']}/videos", params=params, headers=headers)
        response.raise_for_status()
        response.encoding = "utf-8"

        holodex_videos = response.json()

        for holodex_video in holodex_videos:
            video_ids.append(holodex_video['id'])

        if len(holodex_videos) < 50:
            print(f"Fetched {len(video_ids)} video ids from Holodex for channel", channel['en_name'], channel['id'])
            break

    def _serialize(v):
        if isinstance(v, datetime):
            return v.isoformat()
        if v is None:
            return ""
        return str(v)

    existing_ids = existing_ids or set()

    total = len(video_ids)
    for idx, video_id in enumerate(video_ids, start=1):
        if video_id in existing_ids:
            # already present in CSV, skip
            print(f"[{idx}/{total}] Channel: {channel['en_name']} ({channel['id']}) - Video: {video_id} - Skipped (already present)")
            continue
        # fetch and build complete data
        complete_data = {
            **get_video_data(video_id),
            'channel_id': channel['id'],
            'channel_en_name': channel['en_name'],
            'channel_ja_name': channel['ja_name'],
            'channel_en_category': channel['en_category'],
            'channel_ja_category': channel['ja_category'],
        }

        # prepare a flat mapping for CSV writer following fieldnames order
        row = { name: _serialize(complete_data.get(name)) for name in fieldnames }

        # print channel and id to show progress with counter
        print(f"[{idx}/{total}] Channel: {channel['en_name']} ({channel['id']}) - Video: {video_id} - Wrote to CSV")

        csv_writer.writerow(row)

    # no return; streaming to CSV


def get_fieldnames():
    return [
        'video_id',
        'public_time',
        'start_time',
        'end_time',
        'total_time',
        'chat_num_total',
        'chat_num_ja',
        'chat_num_emoji',
        'chat_num_en',
        'uniq_user_num',
        'uniq_member_num',
        'total_super_chat_amount_yen',
        'english_chat_ratio',
        'member_chat_ratio',
        'chat_per_second',
        'max_ccv',
        'member_num',
        'member_gift_num_from',
        'member_gift_num_to',
        'milestone_num',
        'channel_id',
        'channel_en_name',
        'channel_ja_name',
        'channel_en_category',
        'channel_ja_category',
    ]


def load_existing_ids(output_file):
    """Return a set of video_id strings read from existing CSV or empty set."""
    existing_ids = set()
    if not os.path.exists(output_file):
        return existing_ids

    try:
        with open(output_file, 'r', newline='', encoding='utf-8') as readfile:
            reader = csv.DictReader(readfile)
            for row in reader:
                vid = row.get('video_id')
                if vid:
                    existing_ids.add(vid)
    except Exception:
        # if reading fails for any reason, return empty set so we try all
        return set()

    return existing_ids


def process_output_file(output_file, fieldnames):
    """Create or append to CSV, streaming video rows and skipping existing ids."""
    existing_ids = load_existing_ids(output_file)

    if os.path.exists(output_file):
        with open(output_file, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            for channel in channels():
                videos_with_data(channel, writer, fieldnames, existing_ids)
    else:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for channel in channels():
                videos_with_data(channel, writer, fieldnames, existing_ids)


def main():
    output_file = "output/dataset.csv"

    fieldnames = get_fieldnames()

    process_output_file(output_file, fieldnames)

    print(f"Wrote CSV to {output_file}")


if __name__ == "__main__":
    main()
