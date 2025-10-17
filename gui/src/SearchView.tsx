import { useState } from "react";
import {
  Box,
  TextField,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Pagination,
} from "@mui/material";

interface SearchResult {
  type: string;
  resource: string;
  module: string;
  attribute?: string;
  value?: string;
  old_value?: string;
  new_value?: string;
  source?: string;
  severity?: string;
  first_seen?: string;
  last_seen?: string;
  timestamp?: string;
}

const SearchView = () => {
  const [searchTerm, setSearchTerm] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [totalResults, setTotalResults] = useState(0);

  const handleSearch = async (value: string, pageNum: number = 1) => {
    setSearchTerm(value);
    setPage(pageNum);

    if (!value.trim()) {
      setSearchResults([]);
      setTotalPages(0);
      setTotalResults(0);
      return;
    }

    try {
      const response = await fetch("/api/search", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ search: value, page: pageNum }),
      });

      const data = await response.json();
      setSearchResults(data.results || []);
      setTotalPages(data.total_pages || 0);
      setTotalResults(data.total_results || 0);
    } catch (error) {
      console.error("Search error:", error);
      setSearchResults([]);
      setTotalPages(0);
      setTotalResults(0);
    }
  };

  const handlePageChange = (
    _event: React.ChangeEvent<unknown>,
    value: number
  ) => {
    handleSearch(searchTerm, value);
  };

  return (
    <Box sx={{ p: 3 }}>
      <TextField
        fullWidth
        label="Search"
        variant="outlined"
        value={searchTerm}
        onChange={(e) => handleSearch(e.target.value)}
        placeholder="Enter search term..."
        sx={{ mb: 3 }}
      />

      {searchResults.length > 0 && (
        <>
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" color="text.secondary">
              Showing results {(page - 1) * 50 + 1}-
              {Math.min(page * 50, totalResults)} of {totalResults}
            </Typography>
          </Box>

          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Type</TableCell>
                  <TableCell>Resource</TableCell>
                  <TableCell>Module</TableCell>
                  <TableCell>Details</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {searchResults.map((result, index) => (
                  <TableRow key={index}>
                    <TableCell>{result.type}</TableCell>
                    <TableCell>{result.resource}</TableCell>
                    <TableCell>{result.module}</TableCell>
                    <TableCell>
                      {result.type === "observation" && result.attribute && (
                        <>
                          <strong>Attribute:</strong> {result.attribute}
                          <br />
                          <strong>Value:</strong> {result.value}
                          <br />
                          {result.severity && (
                            <>
                              <strong>Severity:</strong> {result.severity}
                              <br />
                            </>
                          )}
                          <strong>First seen:</strong> {result.first_seen}
                          <br />
                          <strong>Last seen:</strong> {result.last_seen}
                        </>
                      )}
                      {result.type === "change" && result.attribute && (
                        <>
                          <strong>Attribute:</strong> {result.attribute}
                          <br />
                          <strong>Old value:</strong> {result.old_value}
                          <br />
                          <strong>New value:</strong> {result.new_value}
                          <br />
                          {result.severity && (
                            <>
                              <strong>Severity:</strong> {result.severity}
                              <br />
                            </>
                          )}
                          <strong>timestamp:</strong> {result.timestamp}
                        </>
                      )}
                      {result.type === "resource" && (
                        <>
                          <strong>Source:</strong> {result.source}
                          <br />
                          <strong>First seen:</strong> {result.first_seen}
                          <br />
                          <strong>Last seen:</strong> {result.last_seen}
                        </>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          {totalPages > 1 && (
            <Box sx={{ display: "flex", justifyContent: "center", mt: 3 }}>
              <Pagination
                count={totalPages}
                page={page}
                onChange={handlePageChange}
                color="primary"
                showFirstButton
                showLastButton
              />
            </Box>
          )}
        </>
      )}

      {searchTerm && searchResults.length === 0 && (
        <Paper sx={{ p: 2 }}>
          <Typography>No results found for "{searchTerm}"</Typography>
        </Paper>
      )}
    </Box>
  );
};

export default SearchView;
