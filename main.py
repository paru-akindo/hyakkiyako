import streamlit as st
import copy
import pandas as pd

# 定数
BOARD_SIZE = 5
DEFAULT_MAX_VALUE = 20

def format_board(board, action=None):
    """
    盤面 (list-of-lists) を pandas の DataFrame に変換する。
    ・None (欠損値) は 0 に置換し、すべて整数で表示。
    ・行・列のラベルは 1～BOARD_SIZE に設定。
    ・オプションの action が指定されている場合（("add", r, c) または ("remove", r, c)）は、
      対象セルを "add" なら赤、"remove" なら青でハイライト。
    ・ヘッダーはグレーにする。
    """
    df = pd.DataFrame(board)
    df = df.fillna(0).astype(int)
    df.index = [i+1 for i in range(len(df))]
    df.columns = [i+1 for i in range(len(df.columns))]

    def highlight_action(df):
        styled = pd.DataFrame("", index=df.index, columns=df.columns)
        if action is not None:
            act_type, act_r, act_c = action
            # DataFrame 上は 1 始まり
            if act_type == "add":
                styled.at[act_r+1, act_c+1] = "background-color: red"
            elif act_type == "remove":
                styled.at[act_r+1, act_c+1] = "background-color: blue"
        return styled

    styler = df.style.apply(highlight_action, axis=None)
    header_styles = [
        {'selector': 'th.col_heading.level0', 'props': 'background-color: lightgray;'},
        {'selector': 'th.row_heading.level0', 'props': 'background-color: lightgray;'}
    ]
    styler = styler.set_table_styles(header_styles)
    return styler

# ----------------------------
# MergeGameSimulator クラス
# ----------------------------
class MergeGameSimulator:
    def __init__(self, board):
        self.board = board  # 初期盤面

    def display_board(self, board, action=None):
        """盤面をテーブル形式で表示（1～BOARD_SIZEのラベル付き、必要なら対象セルに色付け）"""
        st.dataframe(format_board(board, action))
        st.markdown("---")

    def find_clusters(self, board):
        """隣接する同じ数字のクラスターを探す"""
        visited = [[False] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        clusters = []

        def dfs(r, c, value):
            if r < 0 or r >= BOARD_SIZE or c < 0 or c >= BOARD_SIZE:
                return []
            if visited[r][c] or board[r][c] != value:
                return []
            visited[r][c] = True
            cluster = [(r, c)]
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                cluster.extend(dfs(r + dr, c + dc, value))
            return cluster

        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                if board[r][c] is not None and not visited[r][c]:
                    cluster = dfs(r, c, board[r][c])
                    if len(cluster) >= 3:
                        clusters.append(cluster)
        return clusters

    def merge_clusters(self, board, clusters, fall, user_action=None, max_value=20):
        """検出したクラスターを合成する"""
        total_merged_numbers = 0
        for cluster in clusters:
            values = [board[r][c] for r, c in cluster]
            base_value = values[0]
            new_value = base_value + (len(cluster) - 2)
            total_merged_numbers += len(cluster)

            # 操作対象セルを優先する場合など、fall数に応じた選択を行う
            if user_action and user_action[0] == "add":
                if fall == 0:
                    target_r, target_c = user_action[1], user_action[2]
                else:
                    target_r, target_c = min(cluster, key=lambda x: (-x[0], x[1]))
            else:
                target_r, target_c = min(cluster, key=lambda x: (-x[0], x[1]))
            for r, c in cluster:
                board[r][c] = None
            if new_value < max_value:
                board[target_r][target_c] = new_value

        return total_merged_numbers

    def apply_gravity(self, board):
        """各列ごとに数字を下に落下させる"""
        for c in range(BOARD_SIZE):
            column = [board[r][c] for r in range(BOARD_SIZE) if board[r][c] is not None]
            for r in range(BOARD_SIZE - 1, -1, -1):
                board[r][c] = column.pop() if column else None

    def simulate(self, action, max_value=20, suppress_output=False):
        """
        指定したアクション（("add", r, c) または ("remove", r, c)）を盤面に適用し、
        連鎖（合成＋落下）をシミュレートする。
        初期盤面表示時には対象セルをハイライトする。
        """
        board = copy.deepcopy(self.board)
        if not suppress_output:
            st.write("Initial board:")
            self.display_board(board, action=action)
        if action[0] == "add":
            r, c = action[1], action[2]
            if board[r][c] is not None:
                board[r][c] += 1
        elif action[0] == "remove":
            r, c = action[1], action[2]
            board[r][c] = None
        fall_count = 0
        total_merged_numbers = 0
        self.apply_gravity(board)
        while True:
            clusters = self.find_clusters(board)
            if not clusters:
                break
            total_merged_numbers += self.merge_clusters(board, clusters, fall_count, user_action=action, max_value=max_value)
            self.apply_gravity(board)
            fall_count += 1
            if not suppress_output:
                st.write(f"After fall {fall_count}:")
                self.display_board(board)
        return fall_count, total_merged_numbers, board

    def find_best_action(self, max_value=20):
        """
        盤面全体に対して "add" と "remove" 両方を試行し、
        1手の場合の最適な操作（合成セル数優先）を見つける。
        戻り値は辞書 { 'action': (op, r, c), 'merged': merged, 'fall': fall, 'board': board_after }。
        """
        candidates = []
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                if self.board[r][c] is not None:
                    for op in ["add", "remove"]:
                        action = (op, r, c)
                        fall, merged, board_after = self.simulate(action, max_value=max_value, suppress_output=True)
                        candidates.append({
                            'action': action,
                            'merged': merged,
                            'fall': fall,
                            'board': board_after
                        })
        best = max(candidates, key=lambda x: x['merged'])
        return best

    def find_best_action_by_fall(self, max_value=20):
        """
        盤面全体に対して "add" と "remove" 両方を試行し、
        1手の場合の最適な操作（落下回数優先）を見つける。
        戻り値は、find_best_action と同じ形式の辞書を返す。
        """
        candidates = []
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                if self.board[r][c] is not None:
                    for op in ["add", "remove"]:
                        action = (op, r, c)
                        fall, merged, board_after = self.simulate(action, max_value=max_value, suppress_output=True)
                        candidates.append({
                            'action': action,
                            'merged': merged,
                            'fall': fall,
                            'board': board_after
                        })
        best = max(candidates, key=lambda x: x['fall'])
        return best

    def find_best_action_multistep(self, max_value=20, threshold=6):
        """
        1手シミュレーションの最適解をまず求め、合成セル数が threshold 未満の場合は、
        その盤面を初期盤面として2手先までの最適解も評価する。
        ただし、1手目で合成セル数が threshold 以上の場合は、従来通りの1手最適解のみを返す。
        戻り値は辞書 { 'one_move': <候補>, 'two_moves': <2手シーケンスの候補（あれば）> }。
        """
        one_move = self.find_best_action(max_value=max_value)
        result = {'one_move': one_move, 'two_moves': None}
        if one_move['merged'] >= threshold:
            return result
        # 1手目の結果から、2手目候補を探索
        best_total = one_move['merged']
        best_sequence = (one_move['action'], None)
        simul2 = MergeGameSimulator(one_move['board'])
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                if one_move['board'][r][c] is not None:
                    for op in ["add", "remove"]:
                        action2 = (op, r, c)
                        _, merged2, _ = simul2.simulate(action2, max_value=max_value, suppress_output=True)
                        total = one_move['merged'] + merged2
                        if total > best_total:
                            best_total = total
                            best_sequence = (one_move['action'], action2)
        result['two_moves'] = {'actions': best_sequence, 'merged': best_total}
        return result

# ----------------------------
# Streamlit アプリ本体
# ----------------------------
st.title("Merge Game Simulator v2")

# 盤面の入力方法選択
input_method = st.radio("盤面の入力方法を選択", ("グリッド入力", "カンマ区切りテキスト入力"))

# セッション状態の初期化
if "grid_board_values" not in st.session_state:
    st.session_state.grid_board_values = [[8] * BOARD_SIZE for _ in range(BOARD_SIZE)]
if "csv_board_values" not in st.session_state:
    default_csv = "8,8,6,5,6\n8,8,6,5,6\n8,8,6,5,6\n8,8,6,5,6\n8,8,6,5,6"
    st.session_state.csv_board_values = default_csv
if "selected_cell" not in st.session_state:
    st.session_state.selected_cell = None
if "max_value" not in st.session_state:
    st.session_state.max_value = DEFAULT_MAX_VALUE

st.subheader("最大合成値の設定")
st.session_state.max_value = st.number_input("最大合成値 (max_value)", min_value=1,
                                               value=st.session_state.max_value, key="max_value_input")

board = None
# グリッド入力モード
if input_method == "グリッド入力":
    st.subheader("グリッド入力（セルをタップして編集）")
    for r in range(BOARD_SIZE):
        cols = st.columns(BOARD_SIZE)
        for c in range(BOARD_SIZE):
            if cols[c].button(f"({r+1},{c+1}): {st.session_state.grid_board_values[r][c]}", key=f"grid_btn_{r}_{c}"):
                st.session_state.selected_cell = (r, c)
    if st.session_state.selected_cell is not None:
        r, c = st.session_state.selected_cell
        st.subheader(f"({r+1},{c+1}) の値を変更")
        new_value = st.slider("新しい値を選択", min_value=0,
                              max_value=st.session_state.max_value,
                              value=st.session_state.grid_board_values[r][c],
                              key=f"grid_slider_{r}_{c}")
        if st.button("確定", key=f"grid_confirm_{r}_{c}"):
            st.session_state.grid_board_values[r][c] = new_value
            st.session_state.selected_cell = None
        if st.button("キャンセル", key=f"grid_cancel_{r}_{c}"):
            st.session_state.selected_cell = None
    board = st.session_state.grid_board_values
else:
    st.subheader("カンマ区切りテキスト入力")
    csv_input = st.text_area("5行のカンマ区切りで盤面を入力",
                             value=st.session_state.csv_board_values, height=150)
    st.session_state.csv_board_values = csv_input
    try:
        lines = csv_input.strip().splitlines()
        parsed_board = []
        for line in lines:
            values = [int(v.strip()) for v in line.split(",")]
            if len(values) != BOARD_SIZE:
                st.error("各行に5つの数値が必要です。")
                parsed_board = None
                break
            parsed_board.append(values)
        if parsed_board is not None and len(parsed_board) != BOARD_SIZE:
            st.error("5行入力してください。")
            parsed_board = None
    except Exception as e:
        st.error(f"入力解析エラー: {e}")
        parsed_board = None
    board = parsed_board

if board is not None:
    st.subheader("入力された盤面")
    st.dataframe(format_board(board))

simulate_button = st.button("Simulate (最適アクション評価＆連鎖シミュレーション)")

if simulate_button:
    if board is None:
        st.error("盤面が正しく入力されていません。")
    else:
        simulator = MergeGameSimulator(board)
        max_value = st.session_state.max_value
        
        # 1手目の最適解（合成セル数優先）と、落下回数優先の候補をそれぞれ取得
        multi_result = simulator.find_best_action_multistep(max_value=max_value, threshold=6)
        one_move = multi_result['one_move']
        best_by_fall = simulator.find_best_action_by_fall(max_value=max_value)
        
        st.subheader("1手最適解（合成セル数評価）")
        r, c = one_move['action'][1], one_move['action'][2]
        st.write(f"【{one_move['action'][0]}】 ({r+1},{c+1}) → 合成セル数: {one_move['merged']}, 落下回数: {one_move['fall']}")
        st.dataframe(format_board(one_move['board']))
        
        st.subheader("1手最適解（落下回数評価）")
        r2, c2 = best_by_fall['action'][1], best_by_fall['action'][2]
        st.write(f"【{best_by_fall['action'][0]}】 ({r2+1},{c2+1}) → 合成セル数: {best_by_fall['merged']}, 落下回数: {best_by_fall['fall']}")
        st.dataframe(format_board(best_by_fall['board']))
        
        two_moves = multi_result['two_moves']
        if two_moves is not None:
            st.subheader("2手最適解（合成セル数評価）")
            actions = two_moves['actions']
            st.write(f"1手目: 【{actions[0][0]}】 ({actions[0][1]+1},{actions[0][2]+1}), 2手目: 【{actions[1][0]}】 ({actions[1][1]+1},{actions[1][2]+1})")
            st.write(f"合計合成セル数: {two_moves['merged']}")
        else:
            st.write("1手目の最適解の合成セル数が6以上のため、2手先の評価は行いません。")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("シミュレーション結果：1手最適解（合成セル数評価）")
            simulator.simulate(one_move['action'], max_value=max_value, suppress_output=False)
        with col2:
            st.subheader("シミュレーション結果：1手最適解（落下回数評価）")
            simulator.simulate(best_by_fall['action'], max_value=max_value, suppress_output=False)
