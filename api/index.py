import pandas as pd
import random
import os
import json
from datetime import datetime
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import re
from supabase import create_client, Client
from dotenv import load_dotenv

# .envファイルを読み込む（ローカル開発用）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(BASE_DIR, '.env')

# === 環境の診断情報を出力 ===
print("=" * 60)
print("[環境診断] アプリケーション起動")
print(f"[環境診断] BASE_DIR: {BASE_DIR}")
print(f"[環境診断] .env path: {env_path}")
print(f"[環境診断] .env exists: {os.path.exists(env_path)}")

if os.path.exists(env_path):
    print("[環境診断] .envファイルを読み込みます")
    load_dotenv(env_path)
else:
    print("[環境診断] .envファイルが存在しません（Vercel環境の場合は正常）")

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'))
CORS(app)

# --- Supabase Setup ---
supabase: Client = None
try:
    # === 環境変数の診断情報を出力（セキュリティのため値は部分的にマスク）===
    print("-" * 60)
    print("[Supabase診断] 環境変数の読み取り")
    
    # os.environ.get()を使用（Vercel環境でより確実）
    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_KEY')
    
    # 診断情報を出力
    print(f"[Supabase診断] SUPABASE_URL 存在: {supabase_url is not None}")
    if supabase_url:
        print(f"[Supabase診断] SUPABASE_URL 長さ: {len(supabase_url)}")
        print(f"[Supabase診断] SUPABASE_URL 先頭: {supabase_url[:30]}..." if len(supabase_url) > 30 else f"[Supabase診断] SUPABASE_URL: {supabase_url}")
    else:
        print("[Supabase診断] ⚠️ SUPABASE_URL が None です")
    
    print(f"[Supabase診断] SUPABASE_KEY 存在: {supabase_key is not None}")
    if supabase_key:
        print(f"[Supabase診断] SUPABASE_KEY 長さ: {len(supabase_key)}")
        print(f"[Supabase診断] SUPABASE_KEY 先頭: {supabase_key[:20]}..." if len(supabase_key) > 20 else "[Supabase診断] SUPABASE_KEY: (短すぎる)")
    else:
        print("[Supabase診断] ⚠️ SUPABASE_KEY が None です")
    
    # 全環境変数のキー一覧を出力（値は出力しない）
    all_env_keys = list(os.environ.keys())
    supabase_related = [k for k in all_env_keys if 'SUPABASE' in k.upper()]
    print(f"[Supabase診断] Supabase関連の環境変数キー: {supabase_related}")
    print(f"[Supabase診断] 全環境変数の数: {len(all_env_keys)}")
    
    if supabase_url and supabase_key:
        print("[Supabase診断] ✓ 環境変数が設定されています。クライアント作成中...")
        supabase = create_client(supabase_url, supabase_key)
        print("[Supabase診断] ✓ Supabase接続に成功しました。")
    else:
        print("[Supabase診断] ✗ 警告: Supabase環境変数が設定されていません。")
        print("[Supabase診断] データベース機能は利用できません。")
    
    print("=" * 60)
    
except Exception as e:
    print(f"[Supabase診断] ✗ Supabase接続エラー: {e}")
    import traceback
    traceback.print_exc()
    print("=" * 60)

# --- Helper Function ---
def clean_text_line(text):
    if not isinstance(text, str):
        return ""
    # ユーザー名や不要な記号を削除する簡易クリーニング
    cleaned = re.sub(r'^\s*([A-Za-z0-9_]+:|@\w+\s*:|\s*[-\*\d\.]+\s*)', '', text)
    return cleaned.strip().strip('「」')

# --- Main Simulator Class (Updated for Pre-generated CSVs) ---
class TimelineManager:
    def __init__(self):
        self.data_store = {
            'warmup': [],
            'weak': {'0-5': [], '5-10': [], '10-15': []},
            'mid': {'0-5': [], '5-10': [], '10-15': []},
            'strong': {'0-5': [], '5-10': [], '10-15': []}
        }
        self.load_all_data()

    def load_csv(self, filename, text_col='text'):
        path = os.path.join(BASE_DIR, filename) # ルート直下にあると想定
        if not os.path.exists(path):
            # Vercel環境などでは data/ フォルダにある場合も考慮
            path_in_data = os.path.join(BASE_DIR, 'data', filename)
            if os.path.exists(path_in_data):
                path = path_in_data
            else:
                print(f"Warning: File not found: {filename}")
                return []
        
        try:
            df = pd.read_csv(path)
            if text_col not in df.columns and 'Sentence' in df.columns:
                df.rename(columns={'Sentence': text_col}, inplace=True)
            
            if text_col in df.columns:
                df = df.dropna(subset=[text_col])
                # 常に'text'キーに統一する
                result = df[[text_col]].to_dict(orient='records')
                # キー名を'text'に統一
                for item in result:
                    if text_col != 'text' and text_col in item:
                        item['text'] = item.pop(text_col)
                return result
            return []
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            return []

    def load_all_data(self):
        # 1. Warmup (0%)
        self.data_store['warmup'] = self.load_csv('wrime-ver1_converted.csv', text_col='Sentence')

        # 2. Weak Condition
        self.data_store['weak']['0-5'] = self.load_csv('stress_timeline_weak_0-5min_p50.csv')
        self.data_store['weak']['5-10'] = self.load_csv('stress_timeline_weak_5-10min_p69_3.csv')
        self.data_store['weak']['10-15'] = self.load_csv('stress_timeline_weak_10-15min_p70.csv')

        # 3. Mid Condition
        self.data_store['mid']['0-5'] = self.load_csv('stress_timeline_mid_0-5min_p30.csv')
        self.data_store['mid']['5-10'] = self.load_csv('stress_timeline_mid_5-10min_p38.csv')
        self.data_store['mid']['10-15'] = self.load_csv('stress_timeline_mid_10-15min_p52_8.csv')

        # 4. Strong Condition
        self.data_store['strong']['0-5'] = self.load_csv('stress_timeline_strong_0-5min_p10.csv')
        self.data_store['strong']['5-10'] = self.load_csv('stress_timeline_strong_5-10min_p16_9.csv')
        self.data_store['strong']['10-15'] = self.load_csv('stress_timeline_strong_10-15min_p27_2.csv')

    def get_posts(self, condition, phase):
        # phase: 'warmup', '0-5', '5-10', '10-15'
        if phase == 'warmup':
            data = self.data_store['warmup']
            # ウォームアップはランダムに50件ほど抽出
            if data:
                return random.sample(data, min(len(data), 50))
            return []
        
        if condition in self.data_store and phase in self.data_store[condition]:
            return self.data_store[condition][phase]
        
        return []

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400
    
    progress = {'weak': False, 'mid': False, 'strong': False}
    
    # Supabase から完了状況を取得
    if supabase:
        try:
            # experiment_logs テーブルから完了済みレコードを取得
            response = supabase.table('experiment_logs')\
                .select('filter_condition')\
                .eq('participant_name', user_id)\
                .eq('status', 'completed')\
                .execute()
            
            for record in response.data:
                cond = record.get('filter_condition')
                if cond in progress:
                    progress[cond] = True
        except Exception as e:
            print(f"Supabase query error: {e}")
            
    return jsonify({'status': 'ok', 'progress': progress})

@app.route('/api/timeline', methods=['GET'])
def get_timeline():
    condition = request.args.get('condition') # weak, mid, strong
    phase = request.args.get('phase')         # warmup, 0-5, 5-10, 10-15
    
    if not phase:
        return jsonify({'error': 'Phase required'}), 400

    posts = manager.get_posts(condition, phase)
    
    # フロントエンドの期待する形式に整形
    timeline = []
    for p in posts:
        # 'text'キーまたは'Sentence'キーからテキストを取得
        text = p.get('text') or p.get('Sentence', '')
        if text:
            timeline.append({
                'text': clean_text_line(text),
                'source': condition or 'warmup', # 簡易的に条件を入れる
                'stress': 0 # 表示上の色分け用（今回はCSV側で制御済みと仮定し、一律0または適当な値でも可）
            })
    
    return jsonify({
        'success': True,
        'timeline': timeline
    })

def get_phase_to_column_mapping():
    """フェーズをカラム名にマッピングする関数（実際のテーブル構造を確認）"""
    # 実際のカラム名に基づいたデフォルトマッピング
    # 実際のテーブル構造: vas_pre, vas_warmup, vas_phase1, vas_phase2, vas_phase3
    phase_to_column = {
        'pre': 'vas_pre',
        'warmup': 'vas_warmup',
        '0-5': 'vas_phase1',
        '5-10': 'vas_phase2',
        '10-15': 'vas_phase3'
    }
    
    if not supabase:
        return phase_to_column
    
    # 実際のテーブル構造を確認して、異なる命名規則に対応
    try:
        sample_result = supabase.table('experiment_logs')\
            .select('*')\
            .limit(1)\
            .execute()
        
        actual_columns = []
        if sample_result.data and len(sample_result.data) > 0:
            actual_columns = list(sample_result.data[0].keys())
            print(f"[VAS API] Actual columns found: {actual_columns}")
    except Exception as e:
        print(f"[VAS API] Warning: Could not fetch table structure: {e}")
        return phase_to_column
    
    # 実際のカラム名を確認してマッピングを調整（互換性のため）
    if actual_columns:
        # warmup の別名を確認
        if 'vas_warmup' in actual_columns:
            phase_to_column['warmup'] = 'vas_warmup'
        elif 'vas_war' in actual_columns:
            phase_to_column['warmup'] = 'vas_war'
        
        # phase1 (0-5) の別名を確認
        if 'vas_phase1' in actual_columns:
            phase_to_column['0-5'] = 'vas_phase1'
        elif 'vas_phase_0_5' in actual_columns:
            phase_to_column['0-5'] = 'vas_phase_0_5'
        elif 'vas_pha1' in actual_columns:
            phase_to_column['0-5'] = 'vas_pha1'
        
        # phase2 (5-10) の別名を確認
        if 'vas_phase2' in actual_columns:
            phase_to_column['5-10'] = 'vas_phase2'
        elif 'vas_phase_5_10' in actual_columns:
            phase_to_column['5-10'] = 'vas_phase_5_10'
        elif 'vas_pha2' in actual_columns:
            phase_to_column['5-10'] = 'vas_pha2'
        
        # phase3 (10-15) の別名を確認
        if 'vas_phase3' in actual_columns:
            phase_to_column['10-15'] = 'vas_phase3'
        elif 'vas_phase_10_15' in actual_columns:
            phase_to_column['10-15'] = 'vas_phase_10_15'
        elif 'vas_pha3' in actual_columns:
            phase_to_column['10-15'] = 'vas_pha3'
    
    return phase_to_column

@app.route('/api/vas', methods=['POST'])
def save_vas():
    """各フェーズのVASスコアを記録"""
    data = request.json
    user_id = data.get('user_id')
    condition = data.get('condition')
    phase = data.get('phase')  # 'pre', 'warmup', '0-5', '5-10', '10-15'
    vas_score = data.get('vas_score')
    
    print(f"[VAS API] Received request: user_id={user_id}, condition={condition}, phase={phase}, vas_score={vas_score}")
    
    if not user_id or condition not in ['weak', 'mid', 'strong']:
        print(f"[VAS API] Invalid data: user_id={user_id}, condition={condition}")
        return jsonify({'error': 'Invalid data'}), 400
    
    if not phase or phase not in ['pre', 'warmup', '0-5', '5-10', '10-15']:
        print(f"[VAS API] Invalid phase: {phase}")
        return jsonify({'error': 'Invalid phase'}), 400
    
    if vas_score is None:
        print(f"[VAS API] Missing vas_score")
        return jsonify({'error': 'vas_score is required'}), 400
        
    if not supabase:
        print("[VAS API] Supabase not configured")
        return jsonify({'error': 'Database not configured'}), 500
        
    try:
        # フェーズをカラム名にマッピング（共通のヘルパー関数を使用）
        phase_to_column = get_phase_to_column_mapping()
        column_name = phase_to_column.get(phase)
        
        if not column_name:
            print(f"[VAS API] Invalid phase mapping: {phase}")
            return jsonify({'error': 'Invalid phase mapping'}), 400
        
        # カラム名が実際に存在するか確認
        try:
            sample_result = supabase.table('experiment_logs')\
                .select('*')\
                .limit(1)\
                .execute()
            
            actual_columns = []
            if sample_result.data and len(sample_result.data) > 0:
                actual_columns = list(sample_result.data[0].keys())
            
            if actual_columns and column_name not in actual_columns:
                print(f"[VAS API] Warning: Column '{column_name}' not found in actual columns: {actual_columns}")
                # エラーを返す前に、類似のカラム名を探す
                possible_columns = [col for col in actual_columns if 'vas' in col.lower()]
                print(f"[VAS API] Possible VAS columns: {possible_columns}")
                return jsonify({
                    'error': f"Column '{column_name}' not found in table",
                    'available_columns': possible_columns,
                    'phase': phase
                }), 400
        except Exception as e:
            print(f"[VAS API] Warning: Could not verify column existence: {e}")
        
        print(f"[VAS API] Column name: {column_name}")
        
        # 既存のレコードを検索（同じユーザー・条件で最新のもの）
        print(f"[VAS API] Searching for existing record: user_id={user_id}, condition={condition}")
        existing = supabase.table('experiment_logs')\
            .select('id,status')\
            .eq('participant_name', user_id)\
            .eq('filter_condition', condition)\
            .order('id', desc=True)\
            .limit(1)\
            .execute()
        
        print(f"[VAS API] Existing records found: {len(existing.data) if existing.data else 0}")
        
        # 最新のレコードが存在し、未完了（statusがNULLまたは'completed'でない）場合は更新
        if existing.data and len(existing.data) > 0:
            latest_record = existing.data[0]
            record_id = latest_record['id']
            record_status = latest_record.get('status')
            
            print(f"[VAS API] Found record id={record_id}, status={record_status}")
            
            # statusがNULLまたは'completed'でない場合は更新
            if record_status is None or record_status != 'completed':
                update_data = {
                    column_name: int(vas_score)
                }
                # 最後のフェーズ（10-15）の場合はstatusも更新
                if phase == '10-15':
                    update_data['status'] = 'completed'
                
                print(f"[VAS API] Updating record {record_id} with data: {update_data}")
                result = supabase.table('experiment_logs')\
                    .update(update_data)\
                    .eq('id', record_id)\
                    .execute()
                
                print(f"[VAS API] Update result: {result.data if result.data else 'No data returned'}")
                print(f"[VAS API] Successfully updated: {user_id}, {condition}, {phase} ({column_name}) = {vas_score}")
                
                # 更新後のレコードを確認
                verify = supabase.table('experiment_logs')\
                    .select(column_name)\
                    .eq('id', record_id)\
                    .execute()
                print(f"[VAS API] Verification query result: {verify.data if verify.data else 'No data'}")
                
                return jsonify({'status': 'ok', 'message': f'Updated record {record_id}', 'column': column_name, 'value': int(vas_score)})
            else:
                # 完了済みの場合は新規レコードを作成（preフェーズのみ）
                if phase == 'pre':
                    record = {
                        'participant_name': user_id,
                        'filter_condition': condition,
                        column_name: int(vas_score),
                        'status': 'in_progress'
                    }
                    print(f"[VAS API] Creating new record (completed exists): {record}")
                    result = supabase.table('experiment_logs').insert(record).execute()
                    print(f"[VAS API] Insert result: {result.data if result.data else 'No data returned'}")
                    return jsonify({'status': 'ok', 'message': 'Created new record', 'column': column_name, 'value': int(vas_score)})
                else:
                    print(f"[VAS API] Error: Previous experiment completed, but phase is not 'pre'")
                    return jsonify({'error': 'Previous experiment is completed. Please start with pre phase.'}), 400
        else:
            # レコードが存在しない場合は新規作成（preフェーズのみ）
            if phase == 'pre':
                record = {
                    'participant_name': user_id,
                    'filter_condition': condition,
                    column_name: int(vas_score),
                    'status': 'in_progress'
                }
                print(f"[VAS API] Creating new record (no existing): {record}")
                result = supabase.table('experiment_logs').insert(record).execute()
                print(f"[VAS API] Insert result: {result.data if result.data else 'No data returned'}")
                return jsonify({'status': 'ok', 'message': 'Created new record', 'column': column_name, 'value': int(vas_score)})
            else:
                print(f"[VAS API] Error: No existing record found, but phase is not 'pre'")
                return jsonify({'error': 'No existing record found. Please start with pre phase.'}), 400
            
    except Exception as e:
        print(f"[VAS API] Exception occurred: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'type': type(e).__name__}), 500

@app.route('/api/vas/previous', methods=['GET'])
def get_previous_vas():
    """前回のVASスコアを取得"""
    user_id = request.args.get('user_id')
    condition = request.args.get('condition')
    current_phase = request.args.get('current_phase')
    
    if not user_id or condition not in ['weak', 'mid', 'strong']:
        return jsonify({'error': 'Invalid data'}), 400
    
    # フェーズの順序を定義
    phase_order = ['pre', 'warmup', '0-5', '5-10', '10-15']
    
    if current_phase not in phase_order:
        return jsonify({'previous_score': None})
    
    current_index = phase_order.index(current_phase)
    if current_index == 0:
        # 最初のフェーズ（事前）なので前回はない
        return jsonify({'previous_score': None})
    
    # 前のフェーズを取得
    previous_phase = phase_order[current_index - 1]
    
    # フェーズをカラム名にマッピング（共通のヘルパー関数を使用）
    phase_to_column = get_phase_to_column_mapping()
    previous_column = phase_to_column.get(previous_phase)
    if not previous_column:
        return jsonify({'previous_score': None})
    
    if supabase:
        try:
            # 同じユーザー・条件のレコードから前のフェーズのカラムを取得
            response = supabase.table('experiment_logs')\
                .select(previous_column)\
                .eq('participant_name', user_id)\
                .eq('filter_condition', condition)\
                .order('id', desc=True)\
                .limit(1)\
                .execute()
            
            if response.data and len(response.data) > 0:
                previous_score = response.data[0].get(previous_column)
                if previous_score is not None:
                    return jsonify({'previous_score': previous_score})
        except Exception as e:
            print(f"Supabase query error: {e}")
            import traceback
            traceback.print_exc()
            # エラーが発生した場合でもNoneを返す
            return jsonify({'previous_score': None})
    
    return jsonify({'previous_score': None})

@app.route('/api/complete', methods=['POST'])
def complete():
    """実験完了を記録（最後のフェーズ後）"""
    data = request.json
    user_id = data.get('user_id')
    condition = data.get('condition')
    
    if not user_id or condition not in ['weak', 'mid', 'strong']:
        return jsonify({'error': 'Invalid data'}), 400
        
    if supabase:
        try:
            record = {
                'participant_name': user_id,
                'filter_condition': condition,
                'status': 'completed',
                'timestamp': datetime.now().isoformat()
            }
            supabase.table('experiment_logs').insert(record).execute()
            return jsonify({'status': 'ok'})
        except Exception as e:
            print(f"Supabase insert error: {e}")
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'status': 'ok'})

# Vercel用
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=True, port=port)