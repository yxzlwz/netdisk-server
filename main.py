import os  # 操作文件和目录不说了
import random  # 分享码生成等
import re
import shutil  # 删除文件夹
import time  # 日志要用
import urllib
import zipfile  # 下载文件夹时压缩

import requests
from flask import *  # 程序的灵魂
from flask_dropzone import Dropzone

import config

print("-----程序正在初始化-----")

thisDir = os.path.dirname(os.path.abspath(__file__))  # 相对目录
app = Flask(__name__)  # 初始化app对象
dropzone = Dropzone(app)


def zipDir(dir_path, out_full_name):
    zip = zipfile.ZipFile(out_full_name, "w", zipfile.ZIP_DEFLATED)
    for path, dirNames, filenames in os.walk(dir_path):
        f_path = path.replace(dir_path, "")
        for filename in filenames:
            zip.write(os.path.join(path, filename),
                      os.path.join(f_path, filename))
    zip.close()


def folder_name_format(folder_name) -> str:
    if not folder_name:
        return ""
    if folder_name[-1] != "/":
        folder_name = folder_name + "/"
    if folder_name != "/":
        while "//" in folder_name:
            folder_name = folder_name.replace("//", "/")
        while folder_name[0] == "/":
            folder_name = folder_name[1:]
            if not len(folder_name):
                return ""
        return folder_name
    else:
        return ""


def get_up_folder(folder_name):
    folder_name = folder_name_format(folder_name)
    folder_name = folder_name.split("/")
    if len(folder_name) > 1:
        del (folder_name[-1])
        folder_name = "/".join(folder_name) + "/"
        return folder_name
    else:
        return ""


def generate_random_str(random_length=16):
    random_str = ""
    for i in range(random_length):
        random_str += random.choice("ABCDEFGHIGKLMNOPQRSTUVWXYZabcdefghigklmnopqrstuvwxyz0123456789")
    return random_str


def set_path(new_path):
    if not os.path.isdir(new_path):
        os.makedirs(new_path)


def format_size(size: float, dot=1):
    size = int(size)
    if 0 <= size < 1:
        return str(round(size / 0.125, dot)) + " b"
    elif size < 1024:
        return str(round(size, dot)) + " B"
    elif size < 1048576:
        return str(round(size / 1024, dot)) + " KB"
    elif size < 1073741824:
        return str(round(size / 1048576, dot)) + " MB"
    else:
        return str(round(size / 1073741824, dot)) + " GB"


def get_dir_size(dir_path, format_text=True):
    if not os.path.isdir(dir_path):
        dir_path = "%s/files/%s" % (thisDir, dir_path)
    size = 0
    for root, dirs, files in os.walk(dir_path):
        size += sum([os.path.getsize(os.path.join(root, name)) for name in files])
    if format_text:
        return format_size(size)
    else:
        return size


def get_file_size(filepath):
    size = float(os.path.getsize(filepath))
    return format_size(size)


def get_all_folder_files(folder_path, from_path=""):
    result = []
    get_dir = os.listdir(folder_path)
    for i in get_dir:
        sub_dir = os.path.join(folder_path, i)
        if os.path.isdir(sub_dir):
            result = result + [[i + "/", "Folder", get_dir_size(sub_dir), from_path]]
        else:
            result = result + [[i,
                                "." + i.split(".")[-1],
                                get_file_size(folder_path + i),
                                from_path]]
    return result


@app.route("/rename/<path:old_name>", methods=["POST"])
def rename(old_name):
    if "#" in request.form["new_name"]:
        flash("重命名失败：文件名不支持包含#！")
        return redirect("/?path=%s" % (request.args.get("path") if request.args.get("path") else ""))
    if "../" in request.form["new_name"] or "..\\" in request.form["new_name"]:
        flash("新建目录失败：同志，请别尝试通过 ../ 的方式修改服务器目录！")
        return redirect("/?path=%s" % request.args.get("path"))
    # 根据传参计算文件具体路径后利用os库重命名文件并刷新当前页
    new_name = (folder_name_format(request.args.get("path")) if request.args.get("path") else "") + request.form[
        "new_name"]
    old_name = "%s/%s/%s/%s" % (thisDir, "files",
                                request.args.get("path"), old_name)
    if not new_name.endswith(old_name.split(".")[-1]) and os.path.isfile(old_name):
        new_name = new_name + "." + old_name.split(".")[-1]
    new_name = "%s/%s/%s" % (thisDir, "files", new_name)
    try:
        os.rename(old_name, new_name)
    except FileExistsError:
        flash("重命名出错：文件\"%s\"已存在，无法保存两个同名文件！" % request.form["new_name"])
    except OSError:
        flash("重命名出错：文件名中存在非法字符！")
    return redirect("/?path=%s" %
                    (folder_name_format(request.args.get("path"))
                     if request.args.get("path") else ""))


@app.route("/deletes", methods=["POST", "DELETE"])
def deletes():
    files = request.values.to_dict()["data"][1:].split(",|")
    filepath = "%s/%s/%s/" % (thisDir,
                              "files",
                              session.get("username"))
    for i in files:
        try:
            os.remove(filepath + i)
        except FileNotFoundError:
            flash("删除失败：没有找到文件\"%s\"！" % filepath)
    return "/?path=" + folder_name_format(request.args.get("path"))


@app.route("/delete/<path:filepath>", methods=["POST", "DELETE"])
def delete(filepath):
    filepath = request.args.get("path") + filepath
    filepath = "%s/%s/%s" % (thisDir, "files", filepath.replace("%2F", "/"))
    filepath = filepath.replace("//", "/").replace("//", "/")
    if os.path.isdir(filepath):
        try:
            shutil.rmtree(filepath)
        except FileNotFoundError:
            flash("删除失败：没有找到文件夹\"%s\"！" % filepath)
    else:
        try:
            os.remove(filepath)
        except FileNotFoundError:
            flash("删除失败：没有找到文件\"%s\"！" % filepath)
    return redirect("/?path=%s" % folder_name_format(request.args.get("path")))


@app.route("/set-dir", methods=["POST"])
def set_dir():
    new_name = request.form.get("new_folder_name")
    if "../" in new_name or "..\\" in new_name:
        flash("新建目录失败：同志，请别尝试通过 ../ 或 ..\\ 的方式修改服务器目录！")
        return redirect("/?path=%s" % (request.args.get("path")))
    elif "+" in new_name:
        flash("新建目录失败：不接受带有“+”的文件夹名称！")
        return redirect("/?path=%s" % (request.args.get("path")))
    dir_path = "%s/files/%s/%s" % (thisDir,
                                   request.args.get("path"),
                                   new_name)
    try:
        set_path(dir_path)
    except NotADirectoryError:
        flash("新建目录失败：目录名称无效。")
    except OSError:
        flash("新建目录失败：文件夹名称非法。")
    finally:
        return redirect("/?path=%s" % folder_name_format(request.args.get("path")))


@app.route("/download/<path:filename>")
def download_file(filename):
    filename = urllib.parse.unquote(filename)
    filepath = "%s/files/%s" % (thisDir, filename)
    if os.path.isdir(filepath):
        zipDir(filepath, "%s/zip/%s.zip" % (thisDir, filename.replace("/", "-")))
        filepath = "%s/zip/%s.zip" % (thisDir, filename.replace("/", "-"))
    return send_from_directory(filepath, "")


@app.route("/upload", methods=["POST"])
def upload_file():
    f = request.files["file"]
    if "#" in f.filename or "+" in f.filename:
        flash("%s上传失败：文件名不能包含#或+" % f.filename)
        return redirect("/?path=%s" % folder_name_format(request.args.get("path")))
    folder_name = folder_name_format(request.args.get("path"))
    set_path("%s/files/%s" % (thisDir, folder_name))
    upload_path = "%s/%s/%s/%s" % (thisDir, "files", folder_name, f.filename)
    f.save(upload_path)
    f.close()
    return "Success"


@app.route("/", methods=["GET"])
def index():
    # 首页需要确认用户名和IP，方便模板传参和日志处理
    files = "%s/%s/" % (thisDir, "files")
    if request.args.get("path"):
        files = files + folder_name_format(request.args.get("path"))
    if os.path.isdir(files):
        files = get_all_folder_files(files)
    elif os.path.isdir(files.replace(" ", "+")):
        files = get_all_folder_files(files.replace(" ", "+"))
    else:
        flash("访问失败：同志，你的网盘中没有这个目录！")
        return redirect("/")

    if ".." in folder_name_format(request.args.get("path")):
        flash("访问失败：年轻人，访问路径中加入../尝试提权访问可是个危险的行为哦！")
        return redirect("/?path=")

    return render_template("index.html",
                           url=request.url_root[:-1],
                           files=files,
                           folder=folder_name_format(request.args.get("path")),
                           server_title=config.server_title,
                           sum_size=get_dir_size("%s/files/" % thisDir)
                           )


@app.route("/404")
@app.errorhandler(404)
def to_index(info=None):
    flash("访问出错：你刚刚访问了不存在的资源，已为你重定向到主页！")
    return redirect("/")


# 此处是页面定义


if __name__ == "__main__":
    app.run(debug=True, port=config.port, host=config.host)
