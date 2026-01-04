# BioStudio — Windows 本地生信工作站

BioStudio 是一款面向 Windows 用户的本地生信桌面应用，通过可视化界面封装 WSL 后端，让你无需 Linux、无需命令行，即可完成 FastQC、MultiQC、对齐、计数等常见组学分析任务。

它旨在解决生信科研常见痛点：

- Windows 环境难以搭建生信工具链  
- Linux/conda 复杂度高、容易出错  
- 依赖混乱、版本冲突、环境崩溃  
- 生信新手难以快速上手 NGS/组学分析  

BioStudio 让流程变得简单：

> 安装 → 打开 → 点按钮 → 输出结果

## ✨ 功能特性

### 🔧 轻量级本地运行
- 支持 8GB/16GB 内存电脑  
- 自动安装与配置 WSL  
- 环境隔离透明，不暴露 Linux  

### 🧬 组学基础分析
- FastQC / MultiQC  
- Fastp  
- Bowtie2 / HISAT2  
- Samtools  
- FeatureCounts  
- 自动生成表达矩阵  

### 📊 可视化与报告
- 内置报告预览  
- 实时日志  
- 一键导出结果  

### ⚙ 环境管理
- 独立 WSL 环境  
- 自动修复  
- 对用户透明  

### 🧑‍💻 高级模式
- 内置终端  
- 支持自定义命令  

## 📦 安装指南
下载最新版本：  
https://github.com/jinhuili-lab/BioinforStation

双击安装包即可使用。

## 🚀 快速开始
1. 打开 BioStudio  
2. 选择模块  
3. 加载 FASTQ/BAM 文件  
4. 点击 “运行”  
5. 查看结果与日志  
6. 导出文件  

## 📄 License
MIT（免费版）  
商业许可（专业版）

