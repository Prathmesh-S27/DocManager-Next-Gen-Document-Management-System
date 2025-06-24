// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title DocumentLog
 * @dev Contract for logging document management operations
 */
contract DocumentLog {
    // Document action types
    enum ActionType { 
        UPLOAD,     // New document upload
        UPDATE,     // Document metadata update
        DOWNLOAD,   // Document download
        DELETE,     // Document deletion
        VERSION,    // New version upload
        SHARE,      // Document sharing
        RESTORE     // Version restore
    }
    
    // Document operation log entry
    struct LogEntry {
        bytes32 documentId;        // Document identifier
        ActionType action;         // Action performed
        bytes32 userHash;          // User identifier (hashed)
        bytes32 documentHash;      // Document data hash
        bytes32 metadataHash;      // Document metadata hash
        uint256 timestamp;         // When operation occurred
    }
    
    // Root hash for Merkle Tree (document integrity)
    bytes32 public currentMerkleRoot;
    
    // All log entries
    LogEntry[] public logs;
    
    // Maps document ID to its log entry indices
    mapping(bytes32 => uint256[]) public documentLogs;
    
    // Maps user hash to their document actions
    mapping(bytes32 => uint256[]) public userActions;
    
    // System stats
    uint256 public totalDocuments;
    uint256 public totalOperations;
    
    // Events
    event DocumentAction(
        bytes32 indexed documentId,
        uint8 indexed actionType, 
        bytes32 indexed userHash,
        bytes32 documentHash,
        uint256 timestamp
    );
    
    event MerkleRootUpdated(
        bytes32 oldRoot,
        bytes32 newRoot,
        uint256 timestamp
    );
    
    /**
     * @dev Log a document operation
     * @param documentId Document identifier
     * @param action Operation performed
     * @param userHash Hashed user identifier
     * @param documentHash Hash of document content
     * @param metadataHash Hash of document metadata
     */
    function logDocumentAction(
        bytes32 documentId,
        ActionType action,
        bytes32 userHash,
        bytes32 documentHash,
        bytes32 metadataHash
    ) 
        external 
        returns (uint256)
    {
        // Create and store log entry
        LogEntry memory entry = LogEntry({
            documentId: documentId,
            action: action,
            userHash: userHash,
            documentHash: documentHash,
            metadataHash: metadataHash,
            timestamp: block.timestamp
        });
        
        uint256 logIndex = logs.length;
        logs.push(entry);
        
        // Update indices
        documentLogs[documentId].push(logIndex);
        userActions[userHash].push(logIndex);
        
        // Update stats
        totalOperations++;
        
        if (action == ActionType.UPLOAD) {
            totalDocuments++;
        } else if (action == ActionType.DELETE) {
            if (totalDocuments > 0) {
                totalDocuments--;
            }
        }
        
        // Emit event
        emit DocumentAction(
            documentId, 
            uint8(action), 
            userHash, 
            documentHash, 
            block.timestamp
        );
        
        return logIndex;
    }
    
    /**
     * @dev Update the Merkle root to reflect current document state
     * @param newRoot New Merkle root hash
     */
    function updateMerkleRoot(bytes32 newRoot) external {
        bytes32 oldRoot = currentMerkleRoot;
        currentMerkleRoot = newRoot;
        
        emit MerkleRootUpdated(oldRoot, newRoot, block.timestamp);
    }
    
    /**
     * @dev Get all log entries for a document
     * @param documentId Document identifier
     * @return indices Array of log indices for the document
     */
    function getDocumentHistory(bytes32 documentId) 
        external 
        view 
        returns (uint256[] memory) 
    {
        return documentLogs[documentId];
    }
    
    /**
     * @dev Get all actions by a user
     * @param userHash User identifier hash
     * @return indices Array of log indices for the user
     */
    function getUserActions(bytes32 userHash) 
        external 
        view 
        returns (uint256[] memory) 
    {
        return userActions[userHash];
    }
    
    /**
     * @dev Get log entry details
     * @param logIndex Index of the log entry
     * @return documentId The document identifier
     * @return action The action type that was performed
     * @return userHash The hashed user identifier
     * @return documentHash The hash of document content
     * @return metadataHash The hash of document metadata
     * @return timestamp When the operation occurred
     */
    function getLogEntry(uint256 logIndex)
        external
        view
        returns (
            bytes32 documentId,
            ActionType action,
            bytes32 userHash,
            bytes32 documentHash,
            bytes32 metadataHash,
            uint256 timestamp
        )
    {
        require(logIndex < logs.length, "Log index out of bounds");
        
        LogEntry memory entry = logs[logIndex];
        return (
            entry.documentId,
            entry.action,
            entry.userHash,
            entry.documentHash,
            entry.metadataHash,
            entry.timestamp
        );
    }
    
    /**
     * @dev Verify document exists in the log
     * @param documentId Document identifier
     * @return exists Whether document has any log entries
     */
    function documentExists(bytes32 documentId) 
        external 
        view 
        returns (bool) 
    {
        return documentLogs[documentId].length > 0;
    }
    
    /**
     * @dev Get total number of log entries
     * @return count Total log entries
     */
    function getLogCount() external view returns (uint256) {
        return logs.length;
    }
}
