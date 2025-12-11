from elasticsearch import ConnectionError as ESConnectionError
from flask import current_app, jsonify, render_template, request

from app.modules.dataset.models import PublicationType
from app.modules.community.models import Community, CommunityDataSet, CommunityDataSetStatus
from app.modules.explore import explore_bp


@explore_bp.route("/explore", methods=["GET", "POST"])
def index():
    # value = se usa en el filtro (Enum.value) → ej: "conferencepaper"
    # label = se muestra en el select (bonito) → ej: "Conference Paper"
    publication_type_choices = [(pt.value, pt.name.replace("_", " ").title()) for pt in PublicationType]
    community_choices = [(comm.id, comm.name, comm.logo_url) for comm in Community.query.all()]
    return render_template(
        "explore/index.html",
        publication_type_choices=publication_type_choices,
        community_choices=community_choices,
    )


@explore_bp.route("/search")
def search():
    """Legacy endpoint (mantener si hay dependencias en front viejo)."""
    from app.modules.elasticsearch.services import ElasticsearchService

    query = request.args.get("q", "")
    try:
        search_service = ElasticsearchService()
        results = search_service.search(query=query, size=10)
        return jsonify({"results": results})
    except ESConnectionError as exc:
        current_app.logger.warning(
            "Elasticsearch unavailable for legacy search",
            exc_info=exc,
        )
        return jsonify({"error": "Search service unavailable"}), 503
    except Exception as exc:  # pragma: no cover - unexpected path
        current_app.logger.exception(
            "Unexpected error on legacy search",
            exc_info=exc,
        )
        return jsonify({"error": "Unexpected search error"}), 500


@explore_bp.route("/api/v1/search")
def api_search():
    from app.modules.elasticsearch.services import ElasticsearchService

    query = request.args.get("q", "")
    publication_type = request.args.get("publication_type")
    sorting = request.args.get("sorting", "newest")
    tags = request.args.get("tags")
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    community = request.args.get("community")

    page = int(request.args.get("page", 1))
    size = int(request.args.get("size", 10))

    tags_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    try:
        search_service = ElasticsearchService()
    except ESConnectionError as exc:
        current_app.logger.warning("Elasticsearch unavailable", exc_info=exc)
        return (
            jsonify(
                {
                    "error": "Search service unavailable",
                    "details": str(exc),
                }
            ),
            503,
        )
    except Exception as exc:  # pragma: no cover - unexpected path
        current_app.logger.exception(
            "Unexpected error instantiating search service",
            exc_info=exc,
        )
        return jsonify({"error": "Unexpected search error"}), 500

    try:
        results, total = search_service.search(
            query=query,
            publication_type=publication_type,
            sorting=sorting,
            tags=tags_list,
            date_from=date_from,
            date_to=date_to,
            page=page,
            size=size,
        )
    except ESConnectionError as exc:
        current_app.logger.warning(
            "Elasticsearch search failure",
            exc_info=exc,
        )
        return (
            jsonify(
                {
                    "error": "Search service unavailable",
                    "details": str(exc),
                }
            ),
            503,
        )
    except ValueError as exc:
        current_app.logger.info("Invalid search parameters", exc_info=exc)
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # pragma: no cover - unexpected path
        current_app.logger.exception(
            "Unexpected error executing search",
            exc_info=exc,
        )
        return jsonify({"error": "Unexpected search error"}), 500

    if community:
        filtered_results = []
        for result in results:
            dataset_id = result.get("id")
            association = CommunityDataSet.query.filter_by(
                community_id=community,
                dataset_id=dataset_id,
                status=CommunityDataSetStatus.ACCEPTED,
            ).first()
            if association:
                filtered_results.append(result)
        results = filtered_results
        total = len(results)
            
    return jsonify(
        {
            "results": results,
            "total": total,
            "page": page,
            "size": size,
        }
    )
