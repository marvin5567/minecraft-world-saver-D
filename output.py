from flask import Flask, render_template
import queue

app = Flask(__name__)
output_queue = queue.Queue()  # Queue to store outputs

@app.route('/')
def index():
    return render_template('index.html', outputs=list(output_queue.queue))

if __name__ == '__main__':
    app.run(debug=True)
