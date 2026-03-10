class Whiteboard {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.isDrawing = false;
        this.tool = 'pen';
        this.color = '#4ecdc4';
        this.lineWidth = 3;
        this.history = [];
        this.redoStack = [];
        this.startX = 0;
        this.startY = 0;
        this.currentPath = [];

        this.resize();
        window.addEventListener('resize', () => this.resize());
        this.setupEvents();
        this.saveState();
    }

    resize() {
        const container = this.canvas.parentElement;
        if (container) {
            this.canvas.width = container.clientWidth;
            this.canvas.height = container.clientHeight;
            if (this.history.length > 0) {
                this.restoreState(this.history[this.history.length - 1]);
            }
        }
    }

    setupEvents() {
        this.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.onMouseMove(e));
        this.canvas.addEventListener('mouseup', () => this.onMouseUp());
        this.canvas.addEventListener('mouseleave', () => this.onMouseUp());

        this.canvas.addEventListener('touchstart', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            this.onMouseDown({ offsetX: touch.clientX - this.canvas.getBoundingClientRect().left, offsetY: touch.clientY - this.canvas.getBoundingClientRect().top });
        });
        this.canvas.addEventListener('touchmove', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            this.onMouseMove({ offsetX: touch.clientX - this.canvas.getBoundingClientRect().left, offsetY: touch.clientY - this.canvas.getBoundingClientRect().top });
        });
        this.canvas.addEventListener('touchend', () => this.onMouseUp());
    }

    onMouseDown(e) {
        this.isDrawing = true;
        this.startX = e.offsetX;
        this.startY = e.offsetY;
        this.currentPath = [{ x: e.offsetX, y: e.offsetY }];

        if (this.tool === 'pen' || this.tool === 'eraser') {
            this.ctx.beginPath();
            this.ctx.moveTo(e.offsetX, e.offsetY);
        }
    }

    onMouseMove(e) {
        if (!this.isDrawing) return;

        if (this.tool === 'pen') {
            this.ctx.strokeStyle = this.color;
            this.ctx.lineWidth = this.lineWidth;
            this.ctx.lineCap = 'round';
            this.ctx.lineJoin = 'round';
            this.ctx.lineTo(e.offsetX, e.offsetY);
            this.ctx.stroke();
            this.currentPath.push({ x: e.offsetX, y: e.offsetY });
        } else if (this.tool === 'eraser') {
            this.ctx.strokeStyle = '#1a1a2e';
            this.ctx.lineWidth = 20;
            this.ctx.lineCap = 'round';
            this.ctx.lineTo(e.offsetX, e.offsetY);
            this.ctx.stroke();
        }
    }

    onMouseUp() {
        if (this.isDrawing) {
            this.isDrawing = false;
            this.saveState();
        }
    }

    setTool(tool) {
        this.tool = tool;
        this.canvas.style.cursor = tool === 'eraser' ? 'cell' : 'crosshair';
    }

    setColor(color) {
        this.color = color;
    }

    setLineWidth(width) {
        this.lineWidth = width;
    }

    saveState() {
        this.history.push(this.canvas.toDataURL());
        this.redoStack = [];
        if (this.history.length > 50) this.history.shift();
    }

    restoreState(dataUrl) {
        const img = new Image();
        img.onload = () => {
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
            this.ctx.drawImage(img, 0, 0);
        };
        img.src = dataUrl;
    }

    undo() {
        if (this.history.length > 1) {
            this.redoStack.push(this.history.pop());
            this.restoreState(this.history[this.history.length - 1]);
        }
    }

    redo() {
        if (this.redoStack.length > 0) {
            const state = this.redoStack.pop();
            this.history.push(state);
            this.restoreState(state);
        }
    }

    clear() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        this.saveState();
    }

    drawText(text, x, y, color, fontSize) {
        this.ctx.font = `${fontSize || 18}px 'Inter', sans-serif`;
        this.ctx.fillStyle = color || this.color;
        this.ctx.textAlign = 'center';
        this.ctx.fillText(text, x, y);
    }

    drawShape(type, x, y, w, h, color) {
        this.ctx.strokeStyle = color || this.color;
        this.ctx.lineWidth = 2;
        if (type === 'circle') {
            this.ctx.beginPath();
            this.ctx.arc(x, y, w / 2, 0, Math.PI * 2);
            this.ctx.stroke();
        } else if (type === 'rectangle') {
            this.ctx.strokeRect(x - w / 2, y - h / 2, w, h);
        } else if (type === 'arrow') {
            this.ctx.beginPath();
            this.ctx.moveTo(x, y);
            this.ctx.lineTo(x + w, y + h);
            this.ctx.stroke();
            const angle = Math.atan2(h, w);
            this.ctx.beginPath();
            this.ctx.moveTo(x + w, y + h);
            this.ctx.lineTo(x + w - 10 * Math.cos(angle - 0.4), y + h - 10 * Math.sin(angle - 0.4));
            this.ctx.moveTo(x + w, y + h);
            this.ctx.lineTo(x + w - 10 * Math.cos(angle + 0.4), y + h - 10 * Math.sin(angle + 0.4));
            this.ctx.stroke();
        }
    }

    async renderAISteps(steps) {
        for (let i = 0; i < steps.length; i++) {
            const step = steps[i];
            await new Promise(resolve => setTimeout(resolve, 800));

            const x = step.x || (this.canvas.width / 2);
            const y = step.y || (80 + i * 60);
            const color = step.color || '#4ecdc4';

            if (step.type === 'text' || step.type === 'equation') {
                this.drawText(step.content, x, y, color, step.type === 'equation' ? 22 : 18);
            } else if (step.type === 'shape') {
                this.drawShape(step.shape || 'circle', x, y, 60, 60, color);
            } else if (step.type === 'arrow') {
                this.drawShape('arrow', x, y, step.dx || 80, step.dy || 0, color);
            }

            this.saveState();
        }
    }

    exportPNG() {
        return this.canvas.toDataURL('image/png');
    }
}
