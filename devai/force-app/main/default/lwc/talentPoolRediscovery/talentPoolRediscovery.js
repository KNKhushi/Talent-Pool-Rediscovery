import { LightningElement } from 'lwc';
import getLatestResults from '@salesforce/apex/TalentPoolRediscoveryController.getLatestResults';

export default class TalentPoolRediscovery extends LightningElement {

    candidates = [];
    totalResults = 0;
    errorMessage = '';
    isLoading = false;
    hasLoaded = false;

    connectedCallback() {
        this.loadResults();
    }

    async loadResults() {
        this.isLoading = true;
        this.errorMessage = '';

        try {
            const response = await getLatestResults();

            if (
                response.startsWith('ERROR:') ||
                response.startsWith('Python API error:')
            ) {
                throw new Error(response);
            }

            const data = JSON.parse(response);

            this.candidates = (data.results || []).map(
                (candidate, index) => ({
                    ...candidate,
                    rowKey: candidate.Candidate_ID || index,
                    displayRank: candidate.Rank || index + 1,
                    displayScore:
                        candidate.Ranking_Score_Percentage ?? 'N/A'
                })
            );

            this.totalResults = data.total_results || 0;
            this.hasLoaded = true;

        } catch (error) {
            this.errorMessage =
                error.body?.message ||
                error.message ||
                'Unable to retrieve candidate results.';
        } finally {
            this.isLoading = false;
        }
    }

    get hasCandidates() {
        return this.candidates.length > 0;
    }
}