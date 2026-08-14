from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def workflow(name):
    with (ROOT / ".github" / "workflows" / name).open(encoding="utf-8") as file:
        return yaml.safe_load(file)


def workflow_step(job, name):
    for step in job["steps"]:
        if step.get("name") == name:
            return step
    raise AssertionError(f"workflow step not found: {name}")


def test_build_workflow_publishes_only_tagged_spa_images_to_ghcr():
    data = workflow("build.yml")
    triggers = data[True]
    build_job = data["jobs"]["build"]

    assert triggers == {"push": {"tags": ["*"]}}
    assert data["env"] == {
        "REGISTRY": "ghcr.io",
        "IMAGE_NAME": "${{ github.repository }}",
    }
    assert data["permissions"] == {"contents": "read", "packages": "write"}
    assert list(data["jobs"]) == ["build"]

    login = workflow_step(build_job, "Log in to GitHub Container Registry")
    assert login["with"] == {
        "registry": "${{ env.REGISTRY }}",
        "username": "${{ github.actor }}",
        "password": "${{ secrets.GITHUB_TOKEN }}",
    }

    metadata = workflow_step(build_job, "Extract Docker metadata")
    assert metadata["with"]["images"] == "${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}"
    assert metadata["with"]["tags"].splitlines() == [
        "type=ref,event=tag",
        "type=raw,value=latest",
    ]

    image = workflow_step(build_job, "Build and push SPA image")
    assert image["uses"] == "docker/build-push-action@v6"
    assert image["with"]["target"] == "production-spa"
    assert image["with"]["platforms"] == "linux/amd64,linux/arm64"
    assert image["with"]["push"] is True
    assert image["with"]["tags"] == "${{ steps.meta.outputs.tags }}"
    assert image["with"]["labels"] == "${{ steps.meta.outputs.labels }}"
    assert image["with"]["build-args"].strip() == "GIT_VERSION=${{ github.ref_name }}"


def test_build_workflow_does_not_publish_legacy_image_variants_or_use_docker_hub_secrets():
    text = (ROOT / ".github" / "workflows" / "build.yml").read_text(encoding="utf-8")

    assert "production-ssr" not in text
    assert "target: dev" not in text
    assert "docker.io" not in text
    assert "DOCKER_USERNAME" not in text
    assert "DOCKER_PASSWORD" not in text
