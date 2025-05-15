import streamlit as st
import copy
import json
import streamlit.components.v1 as components

# 固定盤面サイズ（5×5）
BOARD_SIZE = 5

#########################################
# シミュレーションロジック (MergeGameSimulator)
#########################################
class MergeGameSimulator:
    def __init__(self, board):
        self.board = board  # board: 2D list of integers; 空セルは None

    def display_board(self, board):
        """盤面を表形式で表示"""
        st.table(board)

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
        """クラスターを合成する。合成されたセル数の総和を返す"""
        total_merged_numbers = 0
        for cluster in clusters:
            values = [board[r][c] for r, c in cluster]
            base_value = values[0]
            new_value = base_value + (len(cluster) - 2)
            total_merged_numbers += len(cluster)

            # 配置位置の決定
            if user_action and user_action[0] == "add":
                if fall == 0:
                    target_r, target_c = user_action[1], user_action[2]
                else:
                    target_r, target_c = min(cluster, key=lambda x: (-x[0], x[1]))
            else:
                target_r, target_c = min(cluster, key=lambda x: (-x[0], x[1]))

            # クラスターを空にする
            for r, c in cluster:
                board[r][c] = None

            # 新しい値を配置（上限値未満なら）
            if new_value < max_value:
                board[target_r][target_c] = new_value

        return total_merged_numbers

    def apply_gravity(self, board):
        """盤面内の数字を下に落とす（重力処理）"""
        for c in range(BOARD_SIZE):
            column = [board[r][c] for r in range(BOARD_SIZE) if board[r][c] is not None]
            for r in range(BOARD_SIZE - 1, -1, -1):
                board[r][c] = column.pop() if column else None

    def simulate(self, action, max_value=20, suppress_output=False):
        """指定の操作を適用してシミュレーションを行い、落下回数、合成セル数、および最終盤面を返す"""
        board = copy.deepcopy(self.board)

        if not suppress_output:
            st.write("Initial board:")
            self.display_board(board)

        # ユーザー操作の適用
        if action[0] == "add":
            r, c = action[1], action[2]
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
        """全セルについて add と remove を試し、落下回数と合成セル数ごとに最適な操作を返す"""
        max_fall_count = 0
        max_total_merged_numbers = 0
        best_action_by_fall = None
        best_action_by_merged = None
        best_action_by_fall_hr = None
        best_action_by_merged_hr = None
        fall_merge_n = 0
        merge_fall_n = 0

        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                if self.board[r][c] is not None:
                    # "add"操作
                    fall_count, merged_count, _ = self.simulate(("add", r, c), max_value=max_value, suppress_output=True)
                    if fall_count >= max_fall_count:
                        max_fall_count = fall_count
                        best_action_by_fall = ("add", r, c)
                        best_action_by_fall_hr = ("add", "row", r+1, "col", c+1)
                        fall_merge_n = merged_count
                    if merged_count >= max_total_merged_numbers:
                        max_total_merged_numbers = merged_count
                        best_action_by_merged = ("add", r, c)
                        best_action_by_merged_hr = ("add", "row", r+1, "col", c+1)
                        merge_fall_n = fall_count

                    # "remove"操作
                    fall_count, merged_count, _ = self.simulate(("remove", r, c), max_value=max_value, suppress_output=True)
                    if fall_count >= max_fall_count:
                        max_fall_count = fall_count
                        best_action_by_fall = ("remove", r, c)
                        best_action_by_fall_hr = ("remove", "row", r+1, "col", c+1)
                        fall_merge_n = merged_count
                    if merged_count >= max_total_merged_numbers:
                        max_total_merged_numbers = merged_count
                        best_action_by_merged = ("remove", r, c)
                        best_action_by_merged_hr = ("remove", "row", r+1, "col", c+1)
                        merge_fall_n = fall_count

        return (best_action_by_fall, max_fall_count,
                best_action_by_merged, max_total_merged_numbers,
                best_action_by_fall_hr, best_action_by_merged_hr,
                fall_merge_n, merge_fall_n)

#########################################
# カスタムDrag & Drop UI (React/JSX)
#########################################
html_code = """
<!DOCTYPE html>
<html>
  <head>
    <meta charset="UTF-8">
    <title>Drag and Drop Board</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
      body { font-family: sans-serif; }
      .container { display: flex; flex-direction: column; align-items: center; }
      .piece-bank {
        display: flex;
        gap: 10px;
        overflow-x: auto;
        margin-bottom: 20px;
      }
      .piece {
        width: 40px;
        height: 40px;
        background-color: #87cefa;
        border: 1px solid #000;
        text-align: center;
        line-height: 40px;
        cursor: grab;
        font-size: 18px;
        user-select: none;
      }
      .board {
        display: grid;
        grid-template-columns: repeat(5, 60px);
        grid-gap: 5px;
        margin-bottom: 20px;
      }
      .cell {
        width: 60px;
        height: 60px;
        border: 1px solid #ccc;
        text-align: center;
        vertical-align: middle;
        line-height: 60px;
        font-size: 24px;
        background-color: #fafafa;
      }
    </style>
    <!-- React, ReactDOM, Babel, and react-beautiful-dnd -->
    <script crossorigin src="https://unpkg.com/react@17/umd/react.development.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom@17/umd/react-dom.development.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <script src="https://unpkg.com/react-beautiful-dnd@13.1.0/dist/react-beautiful-dnd.min.js"></script>
  </head>
  <body>
    <div id="root"></div>
    <button onclick="sendData()">Send Board Configuration</button>
    <pre id="boardState" style="border:1px solid #ccc; padding:10px; width:320px; height:150px; overflow:auto;"></pre>
    <script type="text/babel">
      const { DragDropContext, Droppable, Draggable } = window.ReactBeautifulDnd;
      class DragAndDropBoard extends React.Component {
        constructor(props) {
          super(props);
          this.state = {
            pieces: Array.from({ length: 20 }, (_, i) => String(i + 1)),
            board: Array(25).fill("")
          };
          this.onDragEnd = this.onDragEnd.bind(this);
        }
        onDragEnd(result) {
          if (!result.destination) return;
          const { source, destination } = result;
          if (source.droppableId === "pieceBank" && destination.droppableId === "board") {
            const piece = this.state.pieces[source.index];
            const newBoard = [...this.state.board];
            newBoard[destination.index] = piece;
            this.setState({ board: newBoard });
          }
        }
        render() {
          return (
            <DragDropContext onDragEnd={this.onDragEnd}>
              <div className="container">
                <h3>Piece Bank</h3>
                <Droppable droppableId="pieceBank" direction="horizontal" isDropDisabled={true}>
                  {(provided) => (
                    <div className="piece-bank" ref={provided.innerRef} {...provided.droppableProps}>
                      {this.state.pieces.map((piece, index) => (
                        <Draggable key={"piece-" + piece} draggableId={"piece-" + piece} index={index}>
                          {(provided) => (
                            <div className="piece"
                              ref={provided.innerRef}
                              {...provided.draggableProps}
                              {...provided.dragHandleProps}>
                              {piece}
                            </div>
                          )}
                        </Draggable>
                      ))}
                      {provided.placeholder}
                    </div>
                  )}
                </Droppable>
                <h3>Board (5x5)</h3>
                <Droppable droppableId="board" direction="horizontal">
                  {(provided) => (
                    <div className="board" ref={provided.innerRef} {...provided.droppableProps}>
                      {this.state.board.map((cell, index) => (
                        <div className="cell" key={index}>{cell}</div>
                      ))}
                      {provided.placeholder}
                    </div>
                  )}
                </Droppable>
              </div>
            </DragDropContext>
          );
        }
      }
      function sendData() {
        const cells = document.querySelectorAll(".cell");
        const board = [];
        for (let i = 0; i < cells.length; i++) {
          let val = cells[i].innerText;
          if (val === "") { val = 0; } else { val = parseInt(val); }
          board.push(val);
        }
        const board2D = [];
        for (let i = 0; i < 5; i++) {
          board2D.push(board.slice(i*5, i*5+5));
        }
        document.getElementById("boardState").innerText = JSON.stringify(board2D, null, 2);
      }
      ReactDOM.render(<DragAndDropBoard />, document.getElementById("root"));
    </script>
  </body>
</html>
"""

#########################################
# Render Drag-and-Drop UI component
#########################################
components.html(html_code, height=800, scrolling=True)

st.markdown("### Board Configuration from Component")
st.write("1. In the component above, arrange the board by dragging pieces from the Piece Bank and then click **Send Board Configuration**.")
st.write("2. Copy the JSON displayed below and paste it into the text area, then click **Simulate Board** to run the simulation.")

board_json = st.text_area("Paste Board JSON here:", height=150)

if st.button("Simulate Board"):
    try:
        board = json.loads(board_json)
        # Assume board is a 5x5 array of numbers; empty cells are represented as 0 → convert 0 to None.
        for r in range(len(board)):
            for c in range(len(board[r])):
                if board[r][c] == 0:
                    board[r][c] = None
        simulator = MergeGameSimulator(board)
        best_action_by_fall, max_fall_count, best_action_by_merged, max_total_merged_numbers, best_action_by_fall_hr, best_action_by_merged_hr, fall_merge_n, merge_fall_n = simulator.find_best_action(max_value=20)
        st.write(f"**Best action by fall count:** {best_action_by_fall_hr}, Fall count: {max_fall_count}, Merged numbers: {fall_merge_n}")
        st.write(f"**Best action by merged count:** {best_action_by_merged_hr}, Fall count: {merge_fall_n}, Merged numbers: {max_total_merged_numbers}")
        st.write("### Simulation for Best action by fall count:")
        simulator.simulate(best_action_by_fall, max_value=20, suppress_output=False)
        st.write("### Simulation for Best action by merged count:")
        simulator.simulate(best_action_by_merged, max_value=20, suppress_output=False)
    except Exception as e:
        st.error(f"Error parsing board JSON: {e}")
