# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from http import HTTPStatus
from logging import getLogger

from flask_restx import Namespace, Resource

from packit_service.models import KojiBuildModel, optional_time
from packit_service.service.api.parsers import indices, pagination_arguments
from packit_service.service.api.utils import response_maker

logger = getLogger("packit_service")

koji_builds_ns = Namespace("koji-builds", description="Production builds")


@koji_builds_ns.route("")
class KojiBuildsList(Resource):
    @koji_builds_ns.expect(pagination_arguments)
    @koji_builds_ns.response(HTTPStatus.PARTIAL_CONTENT, "Koji builds list follows")
    def get(self):
        """ List all Koji builds. """

        first, last = indices()
        result = []

        for build in KojiBuildModel.get_range(first, last):
            build_dict = {
                "build_id": build.build_id,
                "status": build.status,
                "build_submitted_time": optional_time(build.build_submitted_time),
                "chroot": build.target,
                "web_url": build.web_url,
                # from old data, sometimes build_logs_url is same and sometimes different to web_url
                "build_logs_url": build.build_logs_url,
                "pr_id": build.get_pr_id(),
                "branch_name": build.get_branch_name(),
                "release": build.get_release_tag(),
            }

            project = build.get_project()
            if project:
                build_dict["project_url"] = project.project_url
                build_dict["repo_namespace"] = project.namespace
                build_dict["repo_name"] = project.repo_name

            result.append(build_dict)

        resp = response_maker(
            result,
            status=HTTPStatus.PARTIAL_CONTENT.value,
        )
        resp.headers["Content-Range"] = f"koji-builds {first + 1}-{last}/*"
        return resp


@koji_builds_ns.route("/<int:id>")
@koji_builds_ns.param("id", "Koji build identifier")
class KojiBuildItem(Resource):
    @koji_builds_ns.response(HTTPStatus.OK, "OK, koji build details follow")
    @koji_builds_ns.response(
        HTTPStatus.NOT_FOUND.value, "No info about build stored in DB"
    )
    def get(self, id):
        """A specific koji build details. From koji_build hash, filled by worker."""
        builds_list = KojiBuildModel.get_all_by_build_id(str(id))

        if not builds_list.first():
            return response_maker(
                {"error": "No info about build stored in DB"},
                status=HTTPStatus.NOT_FOUND.value,
            )

        build = builds_list[0]

        build_dict = {
            "build_id": build.build_id,
            "status": build.status,
            "build_start_time": optional_time(build.build_start_time),
            "build_finished_time": optional_time(build.build_finished_time),
            "build_submitted_time": optional_time(build.build_submitted_time),
            "chroot": build.target,
            "web_url": build.web_url,
            # from old data, sometimes build_logs_url is same and sometimes different to web_url
            "build_logs_url": build.build_logs_url,
            "pr_id": build.get_pr_id(),
            "branch_name": build.get_branch_name(),
            "ref": build.commit_sha,
            "release": build.get_release_tag(),
        }

        project = build.get_project()
        if project:
            build_dict["project_url"] = project.project_url
            build_dict["repo_namespace"] = project.namespace
            build_dict["repo_name"] = project.repo_name

        build_dict["srpm_logs"] = build.srpm_build.logs if build.srpm_build else None

        return response_maker(build_dict)
