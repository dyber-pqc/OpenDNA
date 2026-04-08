# OpenDNA R SDK
# Thin wrapper around the OpenDNA FastAPI server.

#' Create an OpenDNA client
#'
#' @param base_url Base URL of the OpenDNA API server (default: http://localhost:8765)
#' @param token Optional PQC bearer token
#' @return A list with the client configuration
#' @export
opendna_client <- function(base_url = "http://localhost:8765", token = NULL) {
  list(base_url = base_url, token = token)
}

.opendna_headers <- function(client) {
  h <- c("Content-Type" = "application/json")
  if (!is.null(client$token)) h <- c(h, "Authorization" = paste("Bearer", client$token))
  httr::add_headers(.headers = h)
}

.opendna_post <- function(client, path, body) {
  resp <- httr::POST(
    paste0(client$base_url, path),
    .opendna_headers(client),
    body = jsonlite::toJSON(body, auto_unbox = TRUE)
  )
  jsonlite::fromJSON(httr::content(resp, "text", encoding = "UTF-8"), simplifyVector = FALSE)
}

.opendna_get <- function(client, path) {
  resp <- httr::GET(paste0(client$base_url, path), .opendna_headers(client))
  jsonlite::fromJSON(httr::content(resp, "text", encoding = "UTF-8"), simplifyVector = FALSE)
}

#' Score a protein sequence (instant, no model)
#' @export
opendna_evaluate <- function(client, sequence) {
  .opendna_post(client, "/v1/evaluate", list(sequence = sequence))
}

#' Fold a sequence with ESMFold. Polls the returned job until completion.
#' @export
opendna_fold <- function(client, sequence, poll_interval = 2, timeout = 600) {
  resp <- .opendna_post(client, "/v1/fold", list(sequence = sequence))
  job_id <- resp$job_id
  t0 <- Sys.time()
  repeat {
    Sys.sleep(poll_interval)
    j <- .opendna_get(client, paste0("/v1/jobs/", job_id))
    if (identical(j$status, "completed")) return(j$result)
    if (identical(j$status, "failed")) stop("fold job failed: ", j$error)
    if (as.numeric(Sys.time() - t0, units = "secs") > timeout) stop("fold timeout")
  }
}

#' Design alternative sequences for a backbone.
#' @export
opendna_design <- function(client, pdb_string, num_candidates = 10) {
  .opendna_post(client, "/v1/design", list(pdb_string = pdb_string, num_candidates = num_candidates))
}

#' Run the full analysis suite on a sequence.
#' @export
opendna_analyze <- function(client, sequence, pdb_string = NULL) {
  .opendna_post(client, "/v1/analyze", list(sequence = sequence, pdb_string = pdb_string))
}

#' Dock a ligand against a protein.
#' @export
opendna_dock <- function(client, pdb_string, ligand_smiles) {
  .opendna_post(client, "/v1/dock", list(pdb_string = pdb_string, ligand_smiles = ligand_smiles))
}

#' Fetch a UniProt accession (returns sequence + metadata).
#' @export
opendna_fetch_uniprot <- function(client, accession) {
  .opendna_post(client, "/v1/fetch_uniprot", list(accession = accession))
}

#' Run a visual workflow graph.
#' @export
opendna_run_workflow <- function(client, workflow, project_id = NULL) {
  .opendna_post(client, "/v1/workflow/run_graph", list(workflow = workflow, project_id = project_id))
}
