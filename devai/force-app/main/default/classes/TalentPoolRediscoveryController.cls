
public with sharing class TalentPoolRediscoveryController {

    @AuraEnabled
    public static String getLatestResults() {
        try {
            HttpRequest req = new HttpRequest();

            req.setEndpoint(
                'callout:TalentPoolRediscoveryAPI/results'
            );

            req.setMethod('GET');
            req.setTimeout(120000);

            Http http = new Http();
            HttpResponse res = http.send(req);

            if (res.getStatusCode() >= 200 &&
                res.getStatusCode() < 300) {

                return res.getBody();
            }

            return 'Python API error: ' +
                res.getStatusCode() + ' - ' +
                res.getBody();

        } catch (Exception e) {
            System.debug(
                LoggingLevel.ERROR,
                e.getMessage()
            );

            return 'ERROR: ' + e.getMessage();
        }
    }
}
