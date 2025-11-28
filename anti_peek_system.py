import cv2
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
from ultralytics import YOLO
import os
from datetime import datetime
import time
import threading
import subprocess
import platform


class AntiPeekSystem:
    def __init__(self):
        # 先初始化所有属性
        self.monitoring = False
        self.current_frame = None
        self.cap = None
        self.alert_threshold = 2  # 先初始化这个属性
        self.alert_cooldown = 10
        self.last_alert_time = 0

        # 创建保存目录
        self.save_dir = "detection_records"
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

        # 尝试初始化摄像头
        self.init_camera()

        # 加载YOLOv8模型
        try:
            self.model = YOLO('yolov8n.pt')
            print("YOLOv8模型加载成功")
        except Exception as e:
            print(f"模型加载失败: {e}")
            messagebox.showerror("错误", f"模型加载失败: {e}")
            return

        # 初始化GUI
        self.setup_gui()

        # 初始日志
        self.log_event("系统初始化完成")
        self.log_event("请点击'开始监控'按钮启动系统")

        # 初始状态
        self.camera_status.config(text="摄像头状态: 已连接", fg="green")

    def init_camera(self):
        """初始化摄像头 - 修复摄像头索引问题"""
        # 释放之前的摄像头
        if self.cap is not None:
            self.cap.release()
            time.sleep(0.5)  # 等待释放完成

        # 先尝试默认摄像头索引0
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # 使用DirectShow后端避免警告
        if self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                print("摄像头 0 初始化成功")
                # 设置摄像头参数
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)  # 提高分辨率
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                self.cap.set(cv2.CAP_PROP_FPS, 30)
                return
            else:
                self.cap.release()

        # 如果0不行，尝试1
        self.cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
        if self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                print("摄像头 1 初始化成功")
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                self.cap.set(cv2.CAP_PROP_FPS, 30)
                return
            else:
                self.cap.release()

        # 尝试其他可能的索引
        for i in range(2, 5):
            self.cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    print(f"摄像头 {i} 初始化成功")
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                    self.cap.set(cv2.CAP_PROP_FPS, 30)
                    return
                else:
                    self.cap.release()

        # 如果没有摄像头可用
        raise Exception("无法找到可用的摄像头，请检查摄像头连接")

    def setup_gui(self):
        """设置GUI界面 - 优化布局，增大视频显示区域"""
        self.root = tk.Tk()
        self.root.title("防偷看监控系统 - YOLOv8")
        self.root.geometry("1200x900")  # 增大窗口尺寸

        # 创建主框架
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 标题
        title_label = tk.Label(main_frame, text="防偷看监控系统", font=("Arial", 18, "bold"))
        title_label.pack(pady=10)

        # 创建左右分栏
        content_frame = tk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # 左侧视频区域
        left_frame = tk.Frame(content_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # 视频显示区域 - 增大尺寸
        video_frame = tk.LabelFrame(left_frame, text="摄像头画面", font=("Arial", 12, "bold"))
        video_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.video_label = tk.Label(video_frame, text="摄像头预览将显示在这里",
                                    bg="black", fg="white",
                                    width=100, height=30)  # 增大显示区域
        self.video_label.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # 状态和控制区域
        control_frame = tk.Frame(left_frame)
        control_frame.pack(fill=tk.X, pady=10)

        # 状态信息
        status_frame = tk.Frame(control_frame)
        status_frame.pack(fill=tk.X, pady=5)

        self.camera_status = tk.Label(status_frame, text="摄像头状态: 未初始化", font=("Arial", 11))
        self.camera_status.pack(side=tk.LEFT, padx=10)

        self.detection_status = tk.Label(status_frame, text="检测状态: 等待开始", font=("Arial", 11))
        self.detection_status.pack(side=tk.LEFT, padx=10)

        # 控制按钮
        button_frame = tk.Frame(control_frame)
        button_frame.pack(fill=tk.X, pady=5)

        self.start_btn = tk.Button(button_frame, text="开始监控", command=self.start_monitoring,
                                   bg="green", fg="white", width=15, height=2, font=("Arial", 10))
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = tk.Button(button_frame, text="停止监控", command=self.stop_monitoring,
                                  bg="red", fg="white", width=15, height=2, font=("Arial", 10))
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.refresh_cam_btn = tk.Button(button_frame, text="刷新摄像头", command=self.refresh_camera,
                                         bg="blue", fg="white", width=15, height=2, font=("Arial", 10))
        self.refresh_cam_btn.pack(side=tk.LEFT, padx=5)

        self.open_folder_btn = tk.Button(button_frame, text="打开图片路径", command=self.open_image_folder,
                                         bg="orange", fg="white", width=15, height=2, font=("Arial", 10))
        self.open_folder_btn.pack(side=tk.LEFT, padx=5)

        # 右侧设置和日志区域
        right_frame = tk.Frame(content_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False, padx=(10, 0))

        # 设置面板
        settings_frame = tk.LabelFrame(right_frame, text="检测设置", font=("Arial", 12, "bold"))
        settings_frame.pack(fill=tk.X, pady=(0, 10))

        # 警报阈值设置
        threshold_frame = tk.Frame(settings_frame)
        threshold_frame.pack(fill=tk.X, pady=5, padx=10)

        tk.Label(threshold_frame, text="警报人数阈值:", font=("Arial", 10)).pack(side=tk.LEFT)
        self.threshold_var = tk.IntVar(value=self.alert_threshold)
        threshold_spinbox = tk.Spinbox(threshold_frame, from_=1, to=10,
                                       textvariable=self.threshold_var, width=5, font=("Arial", 10))
        threshold_spinbox.pack(side=tk.RIGHT, padx=5)

        # 置信度设置
        confidence_frame = tk.Frame(settings_frame)
        confidence_frame.pack(fill=tk.X, pady=5, padx=10)

        tk.Label(confidence_frame, text="检测置信度:", font=("Arial", 10)).pack(side=tk.LEFT)
        self.confidence_var = tk.DoubleVar(value=0.5)
        confidence_scale = tk.Scale(confidence_frame, from_=0.1, to=0.9,
                                    resolution=0.1, orient=tk.HORIZONTAL,
                                    variable=self.confidence_var, length=180, showvalue=True)
        confidence_scale.pack(side=tk.RIGHT, padx=5)

        # 显示尺寸设置
        display_frame = tk.Frame(settings_frame)
        display_frame.pack(fill=tk.X, pady=5, padx=10)

        tk.Label(display_frame, text="显示尺寸:", font=("Arial", 10)).pack(side=tk.LEFT)
        self.display_size_var = tk.StringVar(value="大")
        display_combo = ttk.Combobox(display_frame, textvariable=self.display_size_var,
                                     values=["小", "中", "大", "全屏"], width=8, state="readonly")
        display_combo.pack(side=tk.RIGHT, padx=5)
        display_combo.bind("<<ComboboxSelected>>", self.change_display_size)

        # 日志区域
        log_frame = tk.LabelFrame(right_frame, text="系统日志", font=("Arial", 12, "bold"))
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_frame, height=20, width=40, font=("Arial", 9))
        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=scrollbar.set)

        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)

        # 初始化显示尺寸
        self.display_width = 960
        self.display_height = 720

        # 绑定窗口状态变化事件
        self.root.bind("<Unmap>", self.on_window_minimized)
        self.root.bind("<Map>", self.on_window_restored)

        # 窗口最小化状态标志
        self.window_minimized = False

    def on_window_minimized(self, event):
        """窗口最小化时调用"""
        self.window_minimized = True
        self.log_event("主窗口已最小化，但监控仍在后台运行")

    def on_window_restored(self, event):
        """窗口恢复时调用"""
        self.window_minimized = False
        self.log_event("主窗口已恢复")

    def change_display_size(self, event=None):
        """改变显示尺寸"""
        size = self.display_size_var.get()
        if size == "小":
            self.display_width, self.display_height = 640, 480
        elif size == "中":
            self.display_width, self.display_height = 800, 600
        elif size == "大":
            self.display_width, self.display_height = 960, 720
        elif size == "全屏":
            # 获取屏幕尺寸
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            # 保留一些边距
            self.display_width = screen_width - 100
            self.display_height = screen_height - 200

        self.log_event(f"显示尺寸已更改为: {size} ({self.display_width}x{self.display_height})")

    def open_image_folder(self):
        """打开保存图片的文件夹"""
        try:
            # 获取绝对路径
            abs_path = os.path.abspath(self.save_dir)

            # 根据操作系统使用不同的方法打开文件夹
            if platform.system() == "Windows":
                os.startfile(abs_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", abs_path])
            else:  # Linux
                subprocess.run(["xdg-open", abs_path])

            self.log_event(f"已打开图片保存目录: {abs_path}")
        except Exception as e:
            self.log_event(f"打开文件夹失败: {e}")
            messagebox.showerror("错误", f"无法打开文件夹: {e}")

    def log_event(self, message):
        """记录事件到日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def refresh_camera(self):
        """刷新摄像头连接"""
        self.log_event("正在刷新摄像头连接...")
        self.stop_monitoring()
        try:
            self.init_camera()
            self.log_event("摄像头刷新成功")
            self.camera_status.config(text="摄像头状态: 已连接", fg="green")
        except Exception as e:
            self.log_event(f"摄像头刷新失败: {e}")
            self.camera_status.config(text="摄像头状态: 错误", fg="red")
            messagebox.showerror("摄像头错误", f"无法初始化摄像头: {e}")

    def start_monitoring(self):
        """开始监控"""
        if self.cap is None or not self.cap.isOpened():
            self.log_event("错误: 摄像头未就绪，请先刷新摄像头")
            messagebox.showerror("错误", "摄像头未就绪，请点击'刷新摄像头'")
            return

        self.monitoring = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.detection_status.config(text="检测状态: 运行中", fg="green")
        self.log_event("开始监控")
        self.update_frame()

    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.detection_status.config(text="检测状态: 已停止", fg="red")
        self.log_event("停止监控")

    def detect_people(self, frame):
        """使用YOLOv8检测人数"""
        try:
            confidence_threshold = self.confidence_var.get()
            results = self.model(frame, conf=confidence_threshold, verbose=False)
            people_count = 0

            if len(results) > 0 and results[0].boxes is not None:
                for box in results[0].boxes:
                    if int(box.cls.item()) == 0:  # 人类别
                        people_count += 1

                        # 绘制检测框
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        confidence = box.conf.item()

                        color = (0, 255, 0) if people_count < self.alert_threshold else (0, 0, 255)
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)  # 加粗边框
                        label = f"Person: {confidence:.2f}"
                        cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)  # 增大字体

            # 在画面左上角显示人数统计
            cv2.putText(frame, f"人数: {people_count}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

            # 如果超过阈值，显示警告文字
            if people_count >= self.alert_threshold:
                cv2.putText(frame, "警告! 多人检测!", (10, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

            return frame, people_count
        except Exception as e:
            self.log_event(f"检测错误: {e}")
            return frame, 0

    def save_evidence(self, frame):
        """保存证据"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.save_dir}/alert_{timestamp}.jpg"
        cv2.imwrite(filename, frame)
        return filename

    def show_alert(self, people_count, filename):
        """显示置顶警报窗口"""
        # 如果窗口最小化了，先恢复窗口
        if self.window_minimized:
            self.root.deiconify()  # 恢复窗口显示
            self.root.lift()  # 将窗口置于最前
            self.root.focus_force()  # 强制获取焦点

        # 创建置顶的警报窗口
        alert_window = tk.Toplevel(self.root)
        alert_window.title("安全警告")
        alert_window.geometry("500x300")  # 增大警报窗口以显示更多信息
        alert_window.configure(bg='red')

        # 设置窗口置顶并获取焦点 - 只有警报窗口置顶
        alert_window.attributes('-topmost', True)
        alert_window.focus_force()
        alert_window.grab_set()  # 模态对话框，必须处理完才能继续

        # 让警报窗口出现在屏幕中央
        alert_window.update_idletasks()
        x = (alert_window.winfo_screenwidth() // 2) - (alert_window.winfo_width() // 2)
        y = (alert_window.winfo_screenheight() // 2) - (alert_window.winfo_height() // 2)
        alert_window.geometry(f"+{x}+{y}")

        # 警报内容
        alert_text = (f"⚠️ 安全警告 ⚠️\n\n"
                      f"检测到 {people_count} 个人在屏幕前！\n"
                      f"可能有人正在偷看你的屏幕！\n\n"
                      f"证据已保存: {os.path.basename(filename)}\n"
                      f"保存路径: {os.path.abspath(filename)}")

        alert_label = tk.Label(alert_window,
                               text=alert_text,
                               bg='red', fg='white', font=("Arial", 12, "bold"),
                               justify=tk.LEFT)
        alert_label.pack(expand=True, fill='both', padx=20, pady=20)

        # 按钮框架
        button_frame = tk.Frame(alert_window, bg='red')
        button_frame.pack(pady=10)

        # 确定按钮
        ok_btn = tk.Button(button_frame, text="确 定", command=alert_window.destroy,
                           bg='white', fg='red', font=("Arial", 10, "bold"), width=10, height=1)
        ok_btn.pack(side=tk.LEFT, padx=5)

        # 打开文件夹按钮
        open_btn = tk.Button(button_frame, text="打开图片路径", command=self.open_image_folder,
                             bg='white', fg='blue', font=("Arial", 10, "bold"), width=12, height=1)
        open_btn.pack(side=tk.LEFT, padx=5)

        # 播放系统提示音
        self.root.bell()

        self.log_event(f"警报已触发！检测到 {people_count} 人，证据已保存: {filename}")

    def update_frame(self):
        """更新视频帧"""
        if not self.monitoring:
            return

        try:
            ret, frame = self.cap.read()
            if ret:
                self.current_frame = frame.copy()

                # 更新警报阈值
                self.alert_threshold = self.threshold_var.get()

                # 检测人数
                processed_frame, people_count = self.detect_people(frame)

                # 更新状态
                status_text = f"检测到 {people_count} 人"
                if people_count >= self.alert_threshold:
                    status_text = f"警告! 检测到 {people_count} 人!"
                    self.detection_status.config(fg="red")

                    # 检查冷却时间
                    current_time = time.time()
                    if current_time - self.last_alert_time > self.alert_cooldown:
                        filename = self.save_evidence(self.current_frame)
                        self.show_alert(people_count, filename)
                        self.last_alert_time = current_time
                else:
                    self.detection_status.config(fg="green")

                self.detection_status.config(text=status_text)

                # 显示视频帧 - 使用可调整的显示尺寸
                rgb_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb_frame)
                img = img.resize((self.display_width, self.display_height), Image.LANCZOS)
                imgtk = ImageTk.PhotoImage(image=img)

                # 保持引用，避免被垃圾回收
                self.video_label.imgtk = imgtk
                self.video_label.config(image=imgtk)
            else:
                self.log_event("无法读取摄像头帧")
                self.stop_monitoring()

        except Exception as e:
            self.log_event(f"更新帧时出错: {e}")
            self.stop_monitoring()

        # 继续更新
        self.root.after(30, self.update_frame)

    def run(self):
        """运行应用程序"""
        try:
            self.root.mainloop()
        finally:
            # 确保释放资源
            if self.cap is not None:
                self.cap.release()
            cv2.destroyAllWindows()


if __name__ == "__main__":
    try:
        print("启动防偷看监控系统...")
        app = AntiPeekSystem()
        app.run()
    except Exception as e:
        print(f"程序启动失败: {e}")
        messagebox.showerror("启动错误", f"程序启动失败: {e}")