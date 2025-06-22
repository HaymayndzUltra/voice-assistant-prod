
            $existingRule = Get-NetFirewallRule -DisplayName 'PC2 Services' -ErrorAction SilentlyContinue
            if ($existingRule) {
                Remove-NetFirewallRule -DisplayName 'PC2 Services'
            }
            New-NetFirewallRule -DisplayName 'PC2 Services' -Direction Inbound -Protocol TCP -LocalPort 5581,5615,5563,5590,5596 -Action Allow
            