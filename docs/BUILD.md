# ZenClean 商业打包构建指南

这篇指南记录了如何将开发期的 `ZenClean.py` 源码转制为一个对纯净系统友好的分发级 `.exe` 卡片。

## 1. 依赖挂载 (Dependencies)
普通依赖不足以满足打包所需的“重载编译器”，你需要专门的打包环境库。

请执行：
```bash
pip install -r requirements-dev.txt
```
*这会自动拉取包含 `pyinstaller >= 6.0` 及其以上版本在内的所有依赖项*

## 2. 核心打包设定：zenclean.spec

项目中已经预置了经过精密调试的 `.spec` 定义文件。它主要解决了以下三个痛点：
1. **隐藏导入捕获 (Hidden Imports)**：强制打包入了经常因为反射而丢失的 `send2trash` 及 `machineid`。
2. **多进程分裂控制**：挂载了 `src/hooks/rthook.py` 这个特殊的运行时拦截脚本，并在顶部使用了 `freeze_support()` 挂钩，防止打包成 exe 后子进程无限弹窗死锁。
3. **黑框隐藏**：通过 `console=False` 保证这是纯粹的用户图形界面应用。

## 3. 执行打包操作 (Build Process)

在项目主目录终端执行：
```bash
pyinstaller zenclean.spec --clean
```
如果出现 `Up-to-date` 或缓存错误，添加 `--clean` 参数可以强制清除之前 `build` 文件夹残留。

## 4. 产物目录与验证

打包完成后，您的成果将产生在 `dist/ZenClean/` 目录中。

* **验证点 A (完整性)**：检查该文件夹内是否生成了主入口文件 `ZenClean.exe`，以及 `assets` 和 `config` 文件夹。
* **验证点 B (权限系统)**：当不以管理员身份双击拉起时，是否有 Windows UAC 提权黄盾警报弹出。如若没有，请检查 `main.py` 的首行提权判断是否失效。
