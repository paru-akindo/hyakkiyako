import streamlit as st
import copy

# 固定盤面サイズ
BOARD_SIZE = 5

# カスタムCSSを追加して、st.columns で生成される横ブロックの幅を固定
st.markdown(
    """
    <style>
    /* st.columns で生成される各ブロックの幅を固定し、スマホでも横並びに */
    div[data-testid="stHorizontalBlock"] > div {
        flex: 0 0 60px;
        max-width: 60px;
    }
    
    /* 入力ラベルは非表示に（スマホではスペース節約のため） */
    label[for^="R"] {
        display: none;
    }
    </style>
    """,
    unsafe_allow_html=True
)

######################################
# シミュレーションロジック
######################################
class MergeGameSimulator:
    def __init__(self, board):
        self.board = board  # 2次元リスト。空セルは None

    def display_board(self, board):
        st.table(board)

    def find_clusters(self, board):
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
        total_merged_numbers = 0
        for cluster in clusters:
            values = [board[r][c] for r, c in cluster]
            base_value = values[0]
            new_value = base_value + (len(cluster) - 2)
            total_merged_numbers += len(cluster)
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
        for c in range(BOARD_SIZE):
            column = [board[r][c] for r in range(BOARD_SIZE) if board[r][c] is not None]
            for r in range(BOARD_SIZE - 1, -1, -1):
                board[r][c] = column.pop() if column else None

    def simulate(self, action, max_value=20, suppress_output=False):
        board = copy.deepcopy(self.board)
        if not suppress_output:
            st.write("Initial Board:")
            self.display_board(board)
        if action[0] == "add":
            r, c = action[1], action[2]
            board[r][c] += 1
        elif action[0] == "remove":
            r, c = action[1], action[2]
            board[r][c] = None
        fall_count = 0
        total_merged = 0
        self.apply_gravity(board)
        while True:
            clusters = self.find_clusters(board)
            if not clusters:
                break
            total_merged += self.merge_clusters(board, clusters, fall_count, user_action=action, max_value=max_value)
            self.apply_gravity(board)
            fall_count += 1
            if not suppress_output:
                st.write(f"After fall {fall_count}:")
                self.display_board(board)
        return fall_count, total_merged, board

    def find_best_action(self, max_value=20):
        max_fall = 0
        max_merged = 0
        best_action_fall = None
        best_action_merged = None
        best_action_fall_hr = None
        best_action_merged_hr = None
        fall_merge = 0
        merge_fall = 0
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                if self.board[r][c] is not None:
                    # "add" 操作を試す
                    fall, cnt, _ = self.simulate(("add", r, c), max_value=max_value, suppress_output=True)
                    if fall >= max_fall:
                        max_fall = fall
                        best_action_fall = ("add", r, c)
                        best_action_fall_hr = ("add", "row", r+1, "col", c+1)
                        fall_merge = cnt
                    if cnt >= max_merged:
                        max_merged = cnt
                        best_action_merged = ("add", r, c)
                        best_action_merged_hr = ("add", "row", r+1, "col", c+1)
                        merge_fall = fall
                    # "remove" 操作を試す
                    fall, cnt, _ = self.simulate(("remove", r, c), max_value=max_value, suppress_output=True)
                    if fall >= max_fall:
                        max_fall = fall
                        best_action_fall = ("remove", r, c)
                        best_action_fall_hr = ("remove", "row", r+1, "col", c+1)
                        fall_merge = cnt
                    if cnt >= max_merged:
                        max_merged = cnt
                        best_action_merged = ("remove", r, c)
                        best_action_merged_hr = ("remove", "row", r+1, "col", c+1)
                        merge_fall = fall
        return (best_action_fall, max_fall, best_action_merged, max_merged,
                best_action_fall_hr, best_action_merged_hr, fall_merge, merge_fall)

######################################
# 盤面入力 UI (各セルごとの数値入力)
######################################
st.title("Merge Game Simulator")
st.write("下のグリッドに盤面の各セルの値を入力してください（空の場合は 0 と入力してください）。")

initial_board = []
for r in range(BOARD_SIZE):
    cols = st.columns(BOARD_SIZE)
    row = []
    for c in range(BOARD_SIZE):
        # 例として初期値はすべて 0 （またはお好みの値）
        val = cols[c].number_input(f"R{r+1}C{c+1}", min_value=0, max_value=100, value=0, key=f"{r}_{c}")
        row.append(val)
    initial_board.append(row)

max_value = st.number_input("最大合成値 (max_value):", min_value=1, value=20)

######################################
# シミュレーション実行
######################################
if st.button("Simulate"):
    # 入力盤面の変換: 0 は空セルとして扱う（None に変換）
    board = copy.deepcopy(initial_board)
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c] == 0:
                board[r][c] = None
    st.write("### 入力盤面")
    st.table(initial_board)
    simulator = MergeGameSimulator(board)
    best_action_fall, max_fall, best_action_merged, max_merged, best_action_fall_hr, best_action_merged_hr, fall_merge, merge_fall = simulator.find_best_action(max_value=max_value)
    st.write(f"**Best action by fall:** {best_action_fall_hr}, Fall count: {max_fall}, Merged count: {fall_merge}")
    st.write(f"**Best action by merged count:** {best_action_merged_hr}, Fall count: {merge_fall}, Merged count: {max_merged}")
    st.markdown("#### Simulation (Best action by fall)")
    simulator.simulate(best_action_fall, max_value=max_value, suppress_output=False)
    st.markdown("#### Simulation (Best action by merged count)")
    simulator.simulate(best_action_merged, max_value=max_value, suppress_output=False)
