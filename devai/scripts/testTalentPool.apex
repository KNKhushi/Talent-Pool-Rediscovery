List<Job_Requisition__c> jobs = [
    SELECT Id, Name FROM Job_Requisition__c LIMIT 1
];

if (jobs.isEmpty()) {
    System.debug('ERROR: No Job Requisition found.');
} else {
    String result =
        TalentPoolRediscoveryController.findMatches(jobs[0].Id);
    System.debug(LoggingLevel.ERROR, 'MATCH_RESULT=' + result);
}
