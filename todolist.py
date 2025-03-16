import tkinter as tk
from tkinter import messagebox
import csv
import os
from datetime import datetime

class TodoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("桌面便签工具")
        self.root.geometry("390x600")
        self.root.configure(bg="#f0f0f0")

        self.tasks_by_date = {}
        self.group_states = {}

        self.create_widgets()
        self.load_tasks()
        self.check_alarms_on_startup()
        self.update_time()  # 启动时间更新

    def create_widgets(self):
        # 标题
        title_label = tk.Label(self.root, text="待办事项", font=("SimSun", 16, "bold"), bg="#f0f0f0", fg="#333333")
        title_label.pack(pady=10)

        # 输入框架
        input_frame = tk.Frame(self.root, bg="#f0f0f0")
        input_frame.pack(pady=5)

        # 当前时间显示
        self.time_label = tk.Label(input_frame, text="", font=("SimSun", 12), bg="#f0f0f0", fg="#333333")
        self.time_label.pack(pady=(0, 5))

        # 输入框
        self.entry = tk.Entry(input_frame, width=40, font=("SimSun", 12), bd=2, relief="flat")
        self.entry.pack(pady=(0, 5))  # 修改为垂直布局
        self.entry.focus_set()

        # 添加按钮
        add_button = tk.Button(input_frame, text="添加", command=self.add_task, 
                             font=("SimSun", 10), bg="#4CAF50", fg="white", bd=0, padx=10, pady=5)
        add_button.pack()  # 放在输入框下方

        # 任务显示框架
        self.task_frame = tk.Frame(self.root, bg="#ffffff", bd=1, relief="solid")
        self.task_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.task_frame, bg="#ffffff", highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.task_frame, orient="vertical", command=self.canvas.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.inner_frame = tk.Frame(self.canvas, bg="#ffffff")
        self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

        self.inner_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def update_time(self):
        """更新当前时间显示"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=f"当前时间: {current_time}")
        self.root.after(1000, self.update_time)  # 每秒更新一次

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def toggle_group(self, date, button):
        is_expanded = self.group_states.get(date, True)
        self.group_states[date] = not is_expanded
        button.config(text=f"{'▼' if not is_expanded else '▶'} {date}")
        self.refresh_display()
        self.save_tasks(silent=True)

    def update_completion_time(self, var, time_label, task_text, add_time, date):
        alarm_time_str = "无"
        alarm_message = "无"
        for task in self.tasks_by_date[date]:
            if task[0] == task_text and task[2] == add_time:
                alarm_time_str = task[4]
                alarm_message = task[5]
                break

        if var.get():
            completion_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if alarm_time_str != "无":
                try:
                    alarm_time = datetime.strptime(alarm_time_str, "%Y-%m-%d %H:%M:%S")
                    completion_datetime = datetime.strptime(completion_time, "%Y-%m-%d %H:%M:%S")
                    if alarm_time > completion_datetime:
                        var.set(False)
                        messagebox.showinfo("提示", f"任务 '{task_text}' 的提醒时间晚于完成时间，已取消完成状态并保留提醒")
                        completion_time = "未完成"
                        time_label.config(text=f"添加时间: {add_time}\n完成时间: {completion_time}", fg="#757575")
                        for i, (t_text, _, a_time, _, at, am) in enumerate(self.tasks_by_date[date]):
                            if t_text == task_text and a_time == add_time:
                                self.tasks_by_date[date][i] = (task_text, False, add_time, completion_time, at, am)
                                self.set_alarm_timer(alarm_time, alarm_message, task_text, add_time, date)
                                break
                        self.save_tasks(silent=True)
                        self.refresh_display()
                        return
                except ValueError:
                    pass
            
            time_label.config(text=f"添加时间: {add_time}\n完成时间: {completion_time}", fg="#2E7D32")
            for i, (t_text, _, a_time, _, at, am) in enumerate(self.tasks_by_date[date]):
                if t_text == task_text and a_time == add_time:
                    self.tasks_by_date[date][i] = (task_text, True, add_time, completion_time, at, am)
                    break
        else:
            time_label.config(text=f"添加时间: {add_time}\n完成时间: 未完成", fg="#757575")
            for i, (t_text, _, a_time, _, at, am) in enumerate(self.tasks_by_date[date]):
                if t_text == task_text and a_time == add_time:
                    self.tasks_by_date[date][i] = (task_text, False, add_time, "未完成", at, am)
                    if alarm_time_str != "无":
                        try:
                            alarm_time = datetime.strptime(alarm_time_str, "%Y-%m-%d %H:%M:%S")
                            if alarm_time > datetime.now():
                                self.set_alarm_timer(alarm_time, alarm_message, task_text, add_time, date)
                        except ValueError:
                            pass
                    break
        self.save_tasks(silent=True)
        self.refresh_display()

    def edit_task(self, task_text, add_time, date, label):
        edit_window = tk.Toplevel(self.root)
        edit_window.title("编辑任务")
        edit_window.geometry("300x100")
        edit_window.configure(bg="#f0f0f0")

        tk.Label(edit_window, text="任务内容:", bg="#f0f0f0").pack(pady=5)
        entry = tk.Entry(edit_window, width=40, font=("SimSun", 11))
        entry.pack(pady=5)
        entry.insert(0, task_text)

        def save_edit():
            new_text = entry.get().strip()
            if new_text:
                for i, (t_text, completed, a_time, c_time, at, am) in enumerate(self.tasks_by_date[date]):
                    if t_text == task_text and a_time == add_time:
                        self.tasks_by_date[date][i] = (new_text, completed, a_time, c_time, at, am)
                        break
                self.refresh_display()
                self.save_tasks(silent=True)
                edit_window.destroy()
            else:
                messagebox.showwarning("警告", "任务内容不能为空！")

        tk.Button(edit_window, text="保存", command=save_edit, bg="#4CAF50", fg="white", bd=0).pack(pady=5)

    def delete_task(self, task_text, add_time, date):
        if messagebox.askyesno("确认", "确定删除此任务吗？"):
            for i, (t_text, _, a_time, _) in enumerate(self.tasks_by_date[date]):
                if t_text == task_text and a_time == add_time:
                    del self.tasks_by_date[date][i]
                    break
            if not self.tasks_by_date[date]:
                del self.tasks_by_date[date]
                del self.group_states[date]
            self.refresh_display()
            self.save_tasks(silent=True)

    def add_task(self):
        task_text = self.entry.get().strip()
        if task_text:
            add_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            date = add_time.split()[0]
            if date not in self.tasks_by_date:
                self.tasks_by_date[date] = []
                self.group_states[date] = True
            self.tasks_by_date[date].insert(0, (task_text, False, add_time, "未完成", "无", "无"))
            self.refresh_display()
            self.entry.delete(0, tk.END)
            self.save_tasks(silent=True)
        else:
            messagebox.showwarning("警告", "请输入任务内容！")

    def set_alarm(self, task_text, add_time, date):
        alarm_window = tk.Toplevel(self.root)
        alarm_window.title("设置提醒")
        alarm_window.geometry("400x300")
        alarm_window.configure(bg="#f0f0f0")

        tk.Label(alarm_window, text="提醒日期 (格式: YYYYMMDD, 留空默认当天):", bg="#f0f0f0").pack(pady=5)
        date_entry = tk.Entry(alarm_window, width=40, font=("SimSun", 11))
        date_entry.pack(pady=5)

        tk.Label(alarm_window, text="提醒时间 (格式: HHMMSS或HHMM, 无秒默认为00):", bg="#f0f0f0").pack(pady=5)
        time_entry = tk.Entry(alarm_window, width=40, font=("SimSun", 11))
        time_entry.pack(pady=5)

        tk.Label(alarm_window, text="提醒信息:", bg="#f0f0f0").pack(pady=5)
        message_entry = tk.Entry(alarm_window, width=40, font=("SimSun", 11))
        message_entry.pack(pady=5)

        def save_alarm():
            alarm_date_str = date_entry.get().strip()
            alarm_time_str = time_entry.get().strip()
            alarm_message = message_entry.get().strip()

            if not alarm_date_str:
                alarm_date_str = datetime.now().strftime("%Y%m%d")

            try:
                if len(alarm_time_str) == 4:
                    alarm_time_str += "00"
                alarm_datetime_str = f"{alarm_date_str} {alarm_time_str}"
                alarm_time = datetime.strptime(alarm_datetime_str, "%Y%m%d %H%M%S")
                if alarm_time < datetime.now():
                    messagebox.showwarning("警告", "提醒时间不能早于当前时间！")
                    return
                
                for i, (t_text, completed, a_time, c_time, _, _) in enumerate(self.tasks_by_date[date]):
                    if t_text == task_text and a_time == add_time:
                        if completed and c_time != "未完成":
                            completion_datetime = datetime.strptime(c_time, "%Y-%m-%d %H:%M:%S")
                            if alarm_time > completion_datetime:
                                completed = False
                                c_time = "未完成"
                                messagebox.showinfo("提示", f"任务 '{task_text}' 的提醒时间晚于完成时间，已取消完成状态")
                        
                        self.tasks_by_date[date][i] = (task_text, completed, add_time, c_time, 
                                                    alarm_time.strftime("%Y-%m-%d %H:%M:%S"), alarm_message)
                        break
                
                if not completed:
                    self.set_alarm_timer(alarm_time, alarm_message, task_text, add_time, date)
                
                self.save_tasks(silent=True)
                self.refresh_display()
                alarm_window.destroy()
            except ValueError:
                messagebox.showwarning("警告", "时间格式不正确，请使用 YYYYMMDD HHMMSS 或 YYYYMMDD HHMM 格式！")

        tk.Button(alarm_window, text="保存", command=save_alarm, bg="#4CAF50", fg="white", bd=0).pack(pady=5)

    def set_alarm_timer(self, alarm_time, alarm_message, task_text, add_time, date):
        delay = (alarm_time - datetime.now()).total_seconds() * 1000
        self.root.after(int(delay), lambda: self.show_alarm(alarm_message, task_text, add_time, date))

    def show_alarm(self, alarm_message, task_text, add_time, date):
        for task in self.tasks_by_date[date]:
            if task[0] == task_text and task[2] == add_time and not task[1]:
                messagebox.showinfo("提醒", f"任务: {task_text}\n信息: {alarm_message}")
                break

    def check_alarms_on_startup(self):
        current_time = datetime.now()
        for date in self.tasks_by_date:
            for i, (task_text, completed, add_time, completion_time, alarm_time_str, alarm_message) in enumerate(self.tasks_by_date[date]):
                if alarm_time_str != "无":
                    try:
                        alarm_time = datetime.strptime(alarm_time_str, "%Y-%m-%d %H:%M:%S")
                        if completed and completion_time != "未完成":
                            completion_datetime = datetime.strptime(completion_time, "%Y-%m-%d %H:%M:%S")
                            if alarm_time > completion_datetime:
                                self.tasks_by_date[date][i] = (task_text, False, add_time, "未完成", alarm_time_str, alarm_message)
                                messagebox.showinfo("提示", f"任务 '{task_text}' 的提醒时间晚于完成时间，已取消完成状态")
                                if alarm_time <= current_time:
                                    self.show_alarm(alarm_message, task_text, add_time, date)
                                else:
                                    self.set_alarm_timer(alarm_time, alarm_message, task_text, add_time, date)
                        elif not completed:
                            if alarm_time <= current_time:
                                self.show_alarm(alarm_message, task_text, add_time, date)
                            else:
                                self.set_alarm_timer(alarm_time, alarm_message, task_text, add_time, date)
                    except ValueError:
                        continue
        self.refresh_display()
        self.save_tasks(silent=True)

    def create_task_frame(self, task_text, completed, add_time, completion_time, date):
        task_frame = tk.Frame(self.inner_frame, bg="#fafafa", bd=1, relief="solid", padx=8, pady=8)
        
        var = tk.BooleanVar(value=completed)
        checkbox = tk.Checkbutton(task_frame, variable=var, bg="#fafafa")
        checkbox.pack(side=tk.LEFT, padx=(0, 5))
        
        content_frame = tk.Frame(task_frame, bg="#fafafa")
        content_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        label = tk.Label(content_frame, text=task_text, font=("SimSun", 11, "bold"), 
                        bg="#fafafa", fg="#333333", wraplength=300, justify="left")
        label.pack(anchor="w")
        
        alarm_time = "无"
        alarm_message = "无"
        for t in self.tasks_by_date[date]:
            if t[0] == task_text and t[2] == add_time and len(t) >= 6:
                alarm_time = t[4]
                alarm_message = t[5]
                break
        
        time_text = f"添加时间: {add_time}\n完成时间: {completion_time if completed else '未完成'}"
        if alarm_time != "无" and not completed:
            time_text += f"\n提醒时间: {alarm_time}\n提醒信息: {alarm_message}"
            
        time_label = tk.Label(content_frame, text=time_text, 
                            font=("SimSun", 9), bg="#fafafa", 
                            fg="#2E7D32" if completed else "#757575",
                            height=4, justify="left")
        time_label.pack(anchor="w", pady=2)
        
        button_frame = tk.Frame(task_frame, bg="#fafafa")
        button_frame.pack(side=tk.RIGHT, padx=5)
        
        edit_button = tk.Button(button_frame, text="编辑", font=("SimSun", 11), bg="#2196F3", fg="white", bd=0,
                              command=lambda: self.edit_task(task_text, add_time, date, label))
        edit_button.pack(side=tk.TOP, pady=2)
        
        delete_button = tk.Button(button_frame, text="删除", font=("SimSun", 11), bg="#F44336", fg="white", bd=0,
                                command=lambda: self.delete_task(task_text, add_time, date))
        delete_button.pack(side=tk.TOP, pady=2)
        
        alarm_button = tk.Button(button_frame, text="提醒", font=("SimSun", 11), bg="#FF9800", fg="white", bd=0,
                                command=lambda: self.set_alarm(task_text, add_time, date))
        alarm_button.pack(side=tk.TOP, pady=2)
        
        var.trace("w", lambda *args: self.update_completion_time(var, time_label, task_text, add_time, date))
        return task_frame

    def refresh_display(self):
        for widget in self.inner_frame.winfo_children():
            widget.destroy()

        for date in sorted(self.tasks_by_date.keys(), reverse=True):
            group_frame = tk.Frame(self.inner_frame, bg="#e0e0e0")
            task_count = len(self.tasks_by_date[date])
            toggle_button = tk.Button(group_frame, text=f"{'▼' if self.group_states.get(date, True) else '▶'} {date} ({task_count} 项)", 
                                font=("SimSun", 10, "bold"), bg="#e0e0e0", fg="#333333", bd=0, 
                                command=lambda d=date, btn=group_frame: self.toggle_group(d, btn.winfo_children()[0]))
            toggle_button.pack(side=tk.LEFT, padx=5, pady=2)
            group_frame.pack(fill=tk.X, pady=5)

            if self.group_states.get(date, True):
                for i, (task_text, completed, add_time, completion_time, _, _) in enumerate(self.tasks_by_date[date]):
                    task_frame = self.create_task_frame(task_text, completed, add_time, completion_time, date)
                    task_frame.pack(fill=tk.X, pady=2 if i > 0 else (5, 2))

        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def load_tasks(self):
        if os.path.exists('tasks.csv'):
            with open('tasks.csv', 'r', encoding='utf-8', newline='') as file:
                reader = csv.reader(file)
                for row in reader:
                    if row and len(row) >= 3:
                        task_text = row[0]
                        completed = row[1] == 'True'
                        add_time = row[2]
                        completion_time = row[3] if len(row) > 3 else "未完成"
                        alarm_time = row[4] if len(row) > 4 else "无"
                        alarm_message = row[5] if len(row) > 5 else "无"
                        date = add_time.split()[0]
                        if date not in self.tasks_by_date:
                            self.tasks_by_date[date] = []
                            self.group_states[date] = True
                        self.tasks_by_date[date].append((task_text, completed, add_time, completion_time, 
                                                       alarm_time, alarm_message))

    def save_tasks(self, silent=False):
        with open('tasks.csv', 'w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            for date in sorted(self.tasks_by_date.keys(), reverse=True):
                for task in self.tasks_by_date[date]:
                    writer.writerow(list(task) if len(task) == 6 else list(task) + ["无", "无"])
        if not silent:
            messagebox.showinfo("成功", "任务已保存！")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    app = TodoApp(root)
    app.run()