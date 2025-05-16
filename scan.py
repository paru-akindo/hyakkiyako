import streamlit as st

# **盤面サイズ**
BOARD_SIZE = 5

# **スマホ対応のカスタムCSS**
st.markdown("""
<style>
/* スマホ対応: セルを見やすく調整 */
.cell-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    width: 100%;
}

/* 各セルの見た目を整える */
.cell {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
    max-width: 350px;
    padding: 10px;
    border: 1px solid #ccc;
    background-color: #f9f9f9;
    border-radius: 5px;
}
</style>
""", unsafe_allow_html=True)

######################################
# シミュレーションロジック
######################################
class MergeGameSimulator:
    def __init__(self, board):
        self.board = board  # 2次元リスト。空セルは None

    def display_board(self, board):
        """盤面のテーブル表示"""
        st.table(board)

    def find_clusters(self, board):
        """隣接する同じ数字のクラスターを探す"""
        visited = [[False] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        clusters = []

        def dfs(r, c, value):
            """深さ優先探索でクラスターを探す"""
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
        """クラスターを合成し、合成セル数を返す"""
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
        """数字を下に落とす"""
        for c in range(BOARD_SIZE):
            column = [board[r][c] for r in range(BOARD_SIZE) if board[r][c] is not None]
            for r in range(BOARD_SIZE - 1, -1, -1):
                board[r][c] = column.pop() if column else None

    def simulate(self, action, max_value=20, suppress_output=False):
        """指定の操作を適用してシミュレーションを実行"""
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

######################################
# 盤面入力 UI
######################################
st.title("スマホ対応版 Merge Game Simulator")

# **リスト形式で盤面入力**
st.subheader("数値を調整してください（スライダーで変更可能）")
initial_board = []
for r in range(BOARD_SIZE):
    row = []
    for c in range(BOARD_SIZE):
        val = st.slider(f"セル ({r+1}, {c+1})", min_value=0, max_value=20, value=0, key=f"{r}_{c}")
        row.append(val)
    initial_board.append(row)

# **入力後の盤面を表示**
st.subheader("入力した盤面")
st.table(initial_board)

max_value = st.number_input("最大合成値 (max_value):", min_value=1, value=20)

######################################
# シミュレーション実行
######################################
if st.button("Simulate"):
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
