import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Button, Stack, Typography } from "@mui/material";
import CodeBlock from "./CodeBlock";

function SbomJsonView() {
  const navigate = useNavigate();
  // E.g. cfengine/cfbs/tags/3.27.0, see /api/sboms:
  const { id = "" } = useParams();
  const [sbom, setSbom] = useState({});
  useEffect(() => {
    fetch(`/api/sboms/${id}`)
      .then((response) => response.json())
      .then(setSbom);
  }, [id]);
  const [org, repo, kind, ...name] = id.split("/");
  return (
    <>
      <Stack direction="row" spacing={2} alignItems="center" sx={{ my: 1 }}>
        <Button
          variant="outlined"
          onClick={() => navigate("..", { relative: "path" })}
        >
          Back
        </Button>
        <Typography sx={{ flexGrow: 1 }}>
          {org}/{repo} – {kind === "tags" ? "tag" : "branch"} {name.join("/")}
        </Typography>
        <Button variant="contained" href={`/api/sboms/${id}`}>
          Download
        </Button>
      </Stack>
      <CodeBlock code={JSON.stringify(sbom, null, 2)} />
    </>
  );
}

export default SbomJsonView;
