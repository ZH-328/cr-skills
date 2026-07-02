#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
Aegis Analysis Report Client Script

This script handles authentication and API calls to create analysis reports.
"""

import json
import sys
import os
import argparse
import shutil
import urllib.request
import urllib.error
import urllib.parse
import logging
import subprocess
from configparser import ConfigParser
from typing import Optional, Dict, Any

DEFAULT_SUGGESTION_STATUS = "completed"
DEFAULT_REVIEW_RECORD_STATUS = "completed"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s][%(levelname)s][%(filename)s:%(funcName)s:%(lineno)d] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class ReviewRecord:
    """Lightweight client-side DTO for ReviewRecord.

    This class mirrors the backend `ReviewRecord` model enough to provide a minimal payload
    to create a ReviewRecord via the API. It intentionally defaults non-essential fields
    to keep creation simple.
    """

    def __init__(
        self,
        repo_id: int | None,
        review_id: str,
        project_name: str | None = None,
        review_type: str = "manual",
        author: str | None = None,
        score: float = 0.0,
        develop_manager_id: int = 0,
        source_branch: str | None = None,
        target_branch: str | None = None,
        gitlab_url: str | None = None,
        llm: str | None = None,
        status: str = DEFAULT_REVIEW_RECORD_STATUS,
        feedback_markdown: str | None = None,
        raw_finding_json: Dict[str, Any] | None = None,
    ):
        self.repo_id = (
            int(repo_id) if repo_id is not None and str(repo_id).isdigit() else 0
        )
        self.project_name = project_name or "unknown"
        self.review_id = review_id
        self.review_type = review_type
        self.author = author or "unknown"
        self.score = float(score)
        self.develop_manager_id = int(develop_manager_id)
        self.source_branch = source_branch
        self.target_branch = target_branch
        self.gitlab_url = gitlab_url
        self.llm = llm
        self.status = status
        self.feedback_markdown = feedback_markdown
        self.raw_finding_json = raw_finding_json

    def to_payload(self) -> Dict[str, Any]:
        """Return a dict payload that matches `ReviewRecordSchemaIn` expectations."""
        payload = {
            "repo_id": self.repo_id,
            "project_name": self.project_name,
            "review_id": self.review_id,
            "review_type": self.review_type,
            "author": self.author,
            "score": self.score,
            "develop_manager_id": self.develop_manager_id,
            "source_branch": self.source_branch,
            "target_branch": self.target_branch,
            "gitlab_url": self.gitlab_url,
            "llm": self.llm,
            "status": self.status or DEFAULT_REVIEW_RECORD_STATUS,
            "feedback_markdown": self.feedback_markdown,
            "raw_finding_json": self.raw_finding_json,
        }
        # Remove keys with None values for a minimal payload
        return {k: v for k, v in payload.items() if v is not None}


class ReviewSuggestion:
    """Lightweight client-side DTO for Suggestion model.

    Minimal fields are provided; heavier fields like `matched_rules` can be left out.
    """

    def __init__(
        self,
        review_record_id: int,
        project_name: str,
        title: str = "",
        summary: str = "",
        message: str = "",
        suggestion: str = "",
        severity: str | None = None,
        category: str | None = None,
        file_path: str | None = None,
        line_number_pairs: list | None = None,
        code_url: str | None = None,
        author: str | None = None,
        matched_rules: list | None = None,
        status: str = DEFAULT_SUGGESTION_STATUS,
        project_category: str | None = None,
        feedback_markdown: str | None = None,
        raw_finding_json: Dict[str, Any] | None = None,
        original_severity: str | None = None,
        original_category: str | None = None,
        original_status: str | None = None,
    ):
        self.review_record_id = review_record_id
        self.project_name = project_name
        self.title = title
        self.summary = summary
        self.message = message
        self.suggestion = suggestion
        self.severity = severity
        self.category = category
        self.file_path = file_path
        self.line_number_pairs = line_number_pairs or None
        self.code_url = code_url
        self.author = author
        self.matched_rules = matched_rules
        self.status = status
        self.project_category = project_category
        self.feedback_markdown = feedback_markdown
        self.raw_finding_json = raw_finding_json
        self.original_severity = original_severity
        self.original_category = original_category
        self.original_status = original_status

    def to_payload(self) -> Dict[str, Any]:
        payload = {
            "review_record_id": self.review_record_id,
            "project_name": self.project_name,
            "title": self.title,
            "summary": self.summary,
            "message": self.message,
            "suggestion": self.suggestion,
            "severity": self.severity,
            "category": self.category,
            "file_path": self.file_path,
            "line_number_pairs": self.line_number_pairs,
            "code_url": self.code_url,
            "author": self.author,
            "matched_rules": self.matched_rules,
            "status": self.status or DEFAULT_SUGGESTION_STATUS,
            "project_category": self.project_category,
            "feedback_markdown": self.feedback_markdown,
            "raw_finding_json": self.raw_finding_json,
            "original_severity": self.original_severity,
            "original_category": self.original_category,
            "original_status": self.original_status,
        }
        return {k: v for k, v in payload.items() if v is not None}


class AegisClient:
    """Client for Aegis system"""

    def __init__(self, base_url: str = "http://localhost:8000/api"):
        self.base_url = base_url.rstrip("/")
        self.token = None
        self.user_info = None
        self.headers = {
            "Content-Type": "application/json",
        }

    def login(self, username: str, password: str) -> bool:
        """
        Login to Aegis system

        Args:
            username: Username for login
            password: Password for login

        Returns:
            bool: True if login successful, False otherwise
        """
        login_url = f"{self.base_url}/system/login"

        login_data = {"username": username, "password": password}

        # Use helper to simplify request and unify error handling
        status, json_result = self._safe_request(
            login_url, data=login_data, method="POST", timeout=10
        )
        if status == 2000 and json_result:
            data = json_result.get("result", {})
            if "token" in data:
                self.token = data["token"]
                self.user_info = data.get("userInfo", {})
                # set header
                self.headers["Authorization"] = self.token

                logger.info(
                    f"登录成功！用户: {self.user_info.get('username', 'Unknown')}"
                )
                return True
            else:
                logger.error(f"登录失败: {data.get('msg', '未知错误')}")
                return False
        else:
            logger.error(f"登录请求失败: HTTP {status}")
            return False

    def logout(self) -> bool:
        """
        Logout from the system

        Returns:
            bool: True if logout successful, False otherwise
        """
        if not self.token:
            logger.info("未登录")
            return True

        logout_url = f"{self.base_url}/system/logout"

        status, _ = self._safe_request(logout_url, method="GET", timeout=10)
        if status == 2000:
            logger.info("注销成功")
        else:
            logger.warning(f"注销请求失败: HTTP {status}")

        # Clear local session data
        self.token = None
        self.user_info = None
        if "Authorization" in self.headers:
            del self.headers["Authorization"]

        return True

    def create_review_record(
        self, record_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Create an code review record

        Args:
            record_data: Dictionary containing record data

        Returns:
            Dict containing API response or None if failed
        """
        if not self.token:
            logger.error("未登录，请先使用 login() 方法登录")
            return None

        # endpoints for review record
        endpoint = "/biz/review_record"
        url = f"{self.base_url}{endpoint}"

        # Accept DTO objects as argument
        if isinstance(record_data, ReviewRecord):
            record_data = record_data.to_payload()

        status, json_result = self._safe_request(
            url, data=record_data, method="POST", timeout=30
        )

        if status not in (2000, 201):
            logger.error(f"创建代码评审记录失败 (endpoint: {endpoint}): HTTP {status}")
            return None

        return json_result

    def create_review_suggestion(
        self, suggestion_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Create an code review suggestion

        Args:
            suggestion_data: Dictionary containing suggestion data

        Returns:
            Dict containing API response or None if failed
        """
        if not self.token:
            logger.error("未登录，请先使用 login() 方法登录")
            return None

        # endpoints for review suggestion
        endpoint = "/biz/suggestion"
        url = f"{self.base_url}{endpoint}"

        status, json_result = self._safe_request(
            url, data=suggestion_data, method="POST", timeout=30
        )

        if status not in (2000, 201):
            logger.error(
                f"创建代码评审建议失败 (endpoint: {endpoint}): HTTP {status}, content: {json_result}"
            )
            return None

        return json_result

    def _safe_request(
        self,
        url: str,
        data: Dict[str, Any] = None,
        method: str = "POST",
        timeout: int = 10,
    ) -> tuple[Optional[int], Optional[Dict[str, Any]]]:
        """
        Unified request helper for AegisClient. Handles HTTP/URL and parsing errors.

        Returns:
            (status_code: Optional[int], json_result: Optional[dict])
        """
        try:
            if data is not None:
                payload = json.dumps(data).encode("utf-8")
            else:
                payload = None

            req = urllib.request.Request(
                url, data=payload, headers=self.headers, method=method
            )

            with urllib.request.urlopen(req, timeout=timeout) as response:
                status = response.status
                try:
                    content = response.read().decode("utf-8")
                    json_result = json.loads(content)
                    return json_result.get("code", status), json_result
                except Exception as e:
                    logger.error(f"无法解析响应: {e}")
                    return status, {}

        except urllib.error.HTTPError as e:
            logger.error(f"HTTP错误: {e.code} - {e.reason}")
            try:
                error_content = e.read().decode("utf-8")
                logger.error(f"请求错误详情: {error_content}")
            except Exception:
                pass
            return e.code, None
        except urllib.error.URLError as e:
            logger.error(f"网络连接错误: {e.reason}")
            return None, None
        except Exception as e:
            logger.error(f"未知错误: {e}")
            return None, None


def read_input_file(file_path: str) -> str:
    """
    Read input file content

    Args:
        file_path: Path to the input file

    Returns:
        File content as string
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"错误: 找不到输入文件 '{file_path}'")
        sys.exit(1)
    except Exception as e:
        logger.error(f"错误: 读取文件失败 - {e}")
        sys.exit(1)


def first_line_number(finding: Dict[str, Any]) -> int | None:
    """Return the first line number from supported finding line formats."""
    line = finding.get("line")
    if line is not None:
        return line

    line_pairs = finding.get("line_number_pairs")
    if not line_pairs:
        return None

    first_pair = line_pairs[0]
    if isinstance(first_pair, dict):
        return first_pair.get("start")
    if isinstance(first_pair, (list, tuple)) and first_pair:
        return first_pair[0]

    return None


def assemble_feedback_markdown(finding_data: Dict[str, Any]) -> str:
    """Build structured markdown for one finding, matching backend ReviewService."""
    markdown_parts = []

    markdown_parts.append("## 问题描述")
    file_path = finding_data.get("file")
    line = first_line_number(finding_data)
    message = finding_data.get("message", "发现问题")
    if file_path and line:
        markdown_parts.append(f"在 `{file_path}` 第{line}行发现{message}。")
    else:
        markdown_parts.append(message)

    if finding_data.get("impact"):
        markdown_parts.append("\n## 影响分析")
        markdown_parts.append(finding_data["impact"])

    solution = finding_data.get("solution") or finding_data.get("suggestion")
    if solution:
        markdown_parts.append("\n## 解决方案")
        markdown_parts.append(solution)

    if finding_data.get("prevention"):
        markdown_parts.append("\n## 预防措施")
        markdown_parts.append(finding_data["prevention"])

    markdown_parts.append("\n## 评分")
    if finding_data.get("severity"):
        markdown_parts.append(f"- 严重性: {finding_data['severity']}")
    if finding_data.get("priority"):
        markdown_parts.append(f"- 修复优先级: {finding_data['priority']}")
    if finding_data.get("estimated_time"):
        markdown_parts.append(f"- 预估修复时间: {finding_data['estimated_time']}")

    return "\n".join(markdown_parts)


def build_review_raw_json(
    review_record: Dict[str, Any], findings: list[Dict[str, Any]]
) -> Dict[str, Any]:
    """Build ReviewRecord.raw_finding_json from the upload JSON."""
    if isinstance(review_record.get("raw_finding_json"), dict):
        return review_record["raw_finding_json"]

    score = review_record.get("score", 0)
    raw_json = {
        "summary": review_record.get("summary", f"代码审查完成，总分: {score}分"),
        "total_score": review_record.get("total_score", score),
        "score": score,
        "gitlab_url": review_record.get("gitlab_url"),
        "findings": findings,
    }

    score_breakdown = review_record.get("score_breakdown")
    if score_breakdown:
        raw_json["score_breakdown"] = score_breakdown

    project_category = review_record.get("project_category")
    if project_category:
        raw_json["project_category"] = project_category

    return {k: v for k, v in raw_json.items() if v is not None}


def generate_comprehensive_markdown(json_data: Dict[str, Any]) -> str:
    """Generate ReviewRecord feedback markdown, matching backend ReviewService."""
    markdown_parts = ["# 代码审查报告"]

    markdown_parts.append("\n## 评分")
    total_score = json_data.get("total_score", json_data.get("score", 0))
    markdown_parts.append(f"**总分**: {total_score}分")

    score_breakdown = json_data.get("score_breakdown", {})
    if score_breakdown:
        markdown_parts.append("\n### 评分细分")
        for category, score in score_breakdown.items():
            category_name = {
                "functionality": "功能性",
                "performance": "性能",
                "security": "安全性",
                "best_practices": "最佳实践",
            }.get(category, category)
            markdown_parts.append(f"- **{category_name}**: {score}分")

    findings = json_data.get("findings", [])
    markdown_parts.append("\n## 发现的问题")
    if not findings:
        markdown_parts.append("未发现问题")
        return "\n".join(markdown_parts)

    for index, finding in enumerate(findings, 1):
        severity = (
            str(finding.get("severity", ""))
            .replace("critical", "严重")
            .replace("major", "重要")
            .replace("minor", "次要")
            .replace("info", "信息")
        )
        file_path = finding.get("file", "未指定文件")
        line = first_line_number(finding)
        line_info = f"第{line}行" if line else ""
        title = finding.get("title") or finding.get("id", "未命名问题")

        markdown_parts.append(f"\n### 问题 {index}: {title}")
        markdown_parts.append(f"**严重性**: {severity}")
        markdown_parts.append(f"**位置**: {file_path} {line_info}")
        markdown_parts.append(f"**问题描述**: {finding.get('message', '无描述')}")

        if finding.get("suggestion"):
            markdown_parts.append(f"**改进建议**: {finding.get('suggestion')}")

    return "\n".join(markdown_parts)


def get_cleanup_root(file_path: str) -> str:
    """Return the repository-like root that contains the generated .tmp path."""
    abs_path = os.path.abspath(file_path)
    parts = abs_path.split(os.sep)
    for index in range(len(parts) - 1, -1, -1):
        if parts[index] == ".tmp":
            root_parts = parts[:index]
            if not root_parts:
                return os.sep
            return os.sep.join(root_parts) or os.sep

    return os.getcwd()


def cleanup_review_artifacts(file_path: str) -> None:
    """Delete generated review artifacts after successful upload."""
    cleanup_root = get_cleanup_root(file_path)
    tmp_dir = os.path.join(cleanup_root, ".tmp")
    changelog_path = os.path.join(cleanup_root, "CHANGELOG.md")

    if os.path.isdir(tmp_dir):
        shutil.rmtree(tmp_dir)
        logger.info(f"已删除临时目录: {tmp_dir}")

    if os.path.exists(changelog_path):
        os.remove(changelog_path)
        logger.info(f"已删除 CHANGELOG.md: {changelog_path}")


def get_git_remote_url() -> str:
    """Return origin remote URL from git config."""
    try:
        return (
            subprocess.check_output(["git", "config", "--get", "remote.origin.url"])
            .decode()
            .strip()
        )
    except Exception:
        return ""


def normalize_gitlab_url(git_url: str) -> str:
    """Normalize common GitLab remote URL formats to HTTPS URL."""
    if not git_url:
        return ""

    git_url = git_url.strip()
    if git_url.startswith("git@"):
        return git_url.replace(":", "/", 1).replace("git@", "https://", 1)

    parsed = urllib.parse.urlparse(git_url)
    if parsed.scheme == "ssh" and parsed.hostname:
        netloc = parsed.hostname
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"
        return urllib.parse.urlunparse(("https", netloc, parsed.path, "", "", ""))

    return git_url


def get_gitlab_project_path(gitlab_url: str) -> str:
    """Extract GitLab project path from a remote URL."""
    normalized_url = normalize_gitlab_url(gitlab_url)
    parsed = urllib.parse.urlparse(normalized_url)
    project_path = parsed.path.strip("/")
    if project_path.endswith(".git"):
        project_path = project_path[:-4]
    return project_path


def get_repo_id_from_gitlab_url(
    gitlab_url: str, gitlab_access_token: str = ""
) -> str:
    """Fetch GitLab project id from remote URL via GitLab Projects API."""
    normalized_url = normalize_gitlab_url(gitlab_url)
    parsed = urllib.parse.urlparse(normalized_url)
    project_path = urllib.parse.quote(get_gitlab_project_path(normalized_url), safe="")

    if not parsed.scheme or not parsed.netloc or not project_path:
        return ""

    netloc = parsed.netloc
    if parsed.hostname:
        netloc = parsed.hostname
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"

    api_url = f"{parsed.scheme}://{netloc}/api/v4/projects/{project_path}"
    headers = {}
    if gitlab_access_token:
        headers["GITLAB-ACCESS-TOKEN"] = gitlab_access_token

    try:
        req = urllib.request.Request(api_url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            project_id = data.get("id")
            if project_id is not None:
                return str(project_id)
    except Exception as e:
        logger.warning(f"无法从 GitLab URL 获取 repo_id: {e}")

    return ""


def resolve_repo_metadata(
    args: argparse.Namespace, review_record: Dict[str, Any]
) -> tuple[str, str, str]:
    """Resolve repo id, repo name, and GitLab URL from final review metadata."""
    gitlab_url = normalize_gitlab_url(
        review_record.get("gitlab_url") or args.gitlab_url
    )
    repo_name = args.repo_name or get_gitlab_project_path(gitlab_url)
    repo_id = args.repo_id or get_repo_id_from_gitlab_url(
        gitlab_url, args.gitlab_access_token
    )

    return repo_id, repo_name or "unknown", gitlab_url


def build_review_suggestion(
    finding: Dict[str, Any],
    review_record_id: int,
    project_name: str,
    author: str,
) -> ReviewSuggestion:
    """Build a ReviewSuggestion DTO from one finding."""
    line_pairs = finding.get("line_number_pairs")
    if line_pairs is None:
        line = finding.get("line")
        if line is not None:
            line_pairs = [{"start": line, "end": line}]

    raw_json = (
        finding.get("raw_finding_json")
        if isinstance(finding.get("raw_finding_json"), dict)
        else finding
    )
    feedback_markdown = finding.get("feedback_markdown") or assemble_feedback_markdown(
        finding
    )
    status = finding.get("status", DEFAULT_SUGGESTION_STATUS)

    return ReviewSuggestion(
        review_record_id=review_record_id,
        project_name=project_name,
        title=finding.get("title", "无标题"),
        summary=finding.get("summary", "暂无总结"),
        message=finding.get("message", "暂无信息"),
        suggestion=finding.get("suggestion", "暂无建议"),
        file_path=finding.get("file"),
        line_number_pairs=line_pairs,
        severity=finding.get("severity"),
        category=finding.get("category"),
        project_category=finding.get("project_category"),
        code_url=None,
        author=author,
        matched_rules=finding.get("matched_rule_ids"),
        status=status,
        feedback_markdown=feedback_markdown,
        raw_finding_json=raw_json,
        original_severity=finding.get("original_severity") or finding.get("severity"),
        original_category=finding.get("original_category") or finding.get("category"),
        original_status=finding.get("original_status") or status,
    )


def get_param_value(
    conf: ConfigParser, param_name: str, env_var: str, fallback: str = None
) -> str:
    """
    获取参数值，顺序：conf -> env -> fallback

    Args:
        conf: ConfigParser对象
        param_name: 配置文件中的参数名
        env_var: 环境变量名
        fallback: 默认fallback值

    Returns:
        参数值
    """
    # 1. 先从配置文件获取
    if conf.has_option("DEFAULT", param_name):
        conf_value = conf.get("DEFAULT", param_name).strip()
        if conf_value:
            return conf_value

    # 2. 从环境变量获取
    env_value = os.getenv(env_var)
    if env_value:
        return env_value

    # 3. 特殊方法获取
    if param_name == "AUTHOR":
        # 从 git config 获取作者信息
        try:
            author = (
                subprocess.check_output(["git", "config", "user.name"]).decode().strip()
            )
            if author:
                return author
        except Exception:
            pass
    elif param_name == "GITLAB_URL":
        # 尝试从 git remote 获取 URL
        gitlab_url = normalize_gitlab_url(get_git_remote_url())
        if gitlab_url:
            return gitlab_url
    elif param_name == "SOURCE_BRANCH":
        # 尝试从 git 获取当前分支
        try:
            source_branch = (
                subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"])
                .decode()
                .strip()
            )
            if source_branch:
                return source_branch
        except Exception:
            pass

    # 3. 返回fallback值
    return fallback or ""


def main():
    """Main function"""

    conf = ConfigParser()
    conf.read(os.path.join(os.path.dirname(__file__), "script.conf"))

    parser = argparse.ArgumentParser(description="Aegis代码审查平台")
    parser.add_argument(
        "--base-url",
        type=str,
        help="Aegis API基础URL",
        default=get_param_value(
            conf, "AEGIS_BASE_URL", "AEGIS_BASE_URL", "http://localhost:8000/api"
        ),
    )
    parser.add_argument(
        "--username",
        type=str,
        help="用户名",
        default=get_param_value(conf, "AEGIS_USERNAME", "AEGIS_USERNAME"),
    )
    parser.add_argument(
        "--password",
        type=str,
        help="密码",
        default=get_param_value(conf, "AEGIS_PASSWORD", "AEGIS_PASSWORD"),
    )
    # 创建报告参数
    parser.add_argument(
        "--repo-id",
        type=str,
        help="GitLab项目ID",
        default=get_param_value(conf, "REPO_ID", "CI_MERGE_REQUEST_PROJECT_ID"),
    )
    parser.add_argument(
        "--repo-name",
        type=str,
        help="项目名称",
        default=get_param_value(conf, "REPO_NAME", "CI_MERGE_REQUEST_PROJECT_PATH"),
    )
    parser.add_argument(
        "--gitlab-url",
        type=str,
        help="GitLab项目URL",
        default=get_param_value(conf, "GITLAB_URL", "CI_MERGE_REQUEST_PROJECT_URL"),
    )
    parser.add_argument(
        "--gitlab-access-token",
        type=str,
        help="GitLab GITLAB-ACCESS-TOKEN，用于自动获取REPO_ID",
        default=conf.get("DEFAULT", "GITLAB-ACCESS-TOKEN", fallback="").strip(),
    )
    parser.add_argument(
        "--file-path",
        type=str,
        help="json结果文件路径",
        default=get_param_value(
            conf, "ANALYSIS_REPORT_FILE_PATH", "ANALYSIS_REPORT_FILE_PATH"
        ),
    )
    parser.add_argument(
        "--author",
        type=str,
        help="作者",
        default=get_param_value(conf, "AUTHOR", "CI_COMMIT_AUTHOR"),
    )
    parser.add_argument(
        "--source-branch",
        type=str,
        help="源分支",
        default=get_param_value(
            conf, "SOURCE_BRANCH", "CI_MERGE_REQUEST_SOURCE_BRANCH_NAME"
        ),
    )

    args = parser.parse_args()

    # 参数已经按照 conf -> env -> fallback 的顺序设置了默认值
    username = args.username
    password = args.password

    if not username or not password:
        logger.error("错误: 请提供用户名和密码")
        logger.info("可以通过以下方式提供:")
        logger.info("1. 命令行参数: --username <用户名> --password <密码>")
        logger.info("2. 环境变量: AEGIS_USERNAME, AEGIS_PASSWORD")
        sys.exit(1)

    # Initialize auth helper
    auth = AegisClient(args.base_url)

    # Login
    if not auth.login(username, password):
        logger.error("登录失败，程序退出")
        sys.exit(1)

    # Read input file
    logger.info(f"读取输入文件: {args.file_path}")
    file_content = read_input_file(args.file_path)
    logger.info(f"文件内容长度: {len(file_content)} 字符")
    try:
        data_file = json.loads(file_content)
        if data_file is None or not isinstance(data_file, dict):
            logger.error("输入文件内容为空或格式不正确，期望为JSON对象")
            auth.logout()
            sys.exit(1)
    except Exception:
        logger.error("无法解析输入文件为JSON")
        auth.logout()
        sys.exit(1)

    if "review_record" not in data_file:
        logger.error("输入文件缺少 'review_record' 字段，无法继续")
        auth.logout()
        sys.exit(1)

    review_record = data_file.get("review_record", {})
    findings = data_file.get("findings", [])
    record_raw_finding_json = build_review_raw_json(review_record, findings)
    record_feedback_markdown = review_record.get(
        "feedback_markdown"
    ) or generate_comprehensive_markdown(record_raw_finding_json)
    repo_id, project_name, review_gitlab_url = resolve_repo_metadata(
        args, review_record
    )
    logger.info(
        "项目信息: "
        f"repo_id={repo_id or 'unknown'}, "
        f"project_name={project_name}, "
        f"gitlab_url={review_gitlab_url or 'unknown'}"
    )

    # 创建 ReviewRecord
    rr_dto = ReviewRecord(
        repo_id=repo_id or None,
        review_id="0",
        project_name=project_name,
        review_type="manual",
        author=args.author,
        score=review_record.get("score", 0),
        source_branch=args.source_branch,
        gitlab_url=review_gitlab_url,
        status=review_record.get("status", DEFAULT_REVIEW_RECORD_STATUS),
        feedback_markdown=record_feedback_markdown,
        raw_finding_json=record_raw_finding_json,
    )

    logger.info("正在创建 ReviewRecord")
    rr_res = auth.create_review_record(rr_dto)
    if rr_res is None:
        logger.error("创建 ReviewRecord 失败")
        auth.logout()
        sys.exit(1)
    # rr_res might be dict or contains 'result'
    if isinstance(rr_res, dict) and "result" in rr_res:
        created_rr = rr_res.get("result")
        review_record_id = created_rr.get("id", None)
    else:
        created_rr = rr_res
        review_record_id = created_rr.get("id", None)

    if not review_record_id:
        logger.error(f"无法从创建结果中解析 review_record_id: {created_rr}")
        auth.logout()
        sys.exit(1)

    logger.info(f"ReviewRecord 创建成功: id={review_record_id}")

    # 创建 Suggestions
    created_suggestions = []
    for f in findings:
        try:
            suggestion = build_review_suggestion(
                f, review_record_id, project_name, args.author
            )

            logger.info(
                f"创建 Suggestion: {suggestion.summary} -> {suggestion.file_path}:{suggestion.line_number_pairs}"
            )
            s_res = auth.create_review_suggestion(suggestion.to_payload())
            if s_res:
                created_suggestions.append(s_res)
                # Log created suggestion id if available
                try:
                    sid = s_res.get("result", {}).get("id", None)
                    logger.info(f"Suggestion 创建成功: id={sid}")
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"创建建议失败: {e}")

    logger.info(
        f"已创建 {len(created_suggestions)} 条 Suggestion (ReviewRecord {review_record_id})"
    )
    # Print a minimal summary JSON for caller
    summary = {
        "review_record_id": review_record_id,
        "suggestions_created": len(created_suggestions),
        "tmp_file": args.file_path,
    }
    logger.info(f"上传完成 summary: {json.dumps(summary)}")
    cleanup_review_artifacts(args.file_path)
    # Logout
    auth.logout()


if __name__ == "__main__":
    main()
