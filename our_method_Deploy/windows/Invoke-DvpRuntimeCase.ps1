param(
    [Parameter(Mandatory = $true)]
    [string]$SuitePath,

    [Parameter(Mandatory = $true)]
    [string]$CaseId,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath,

    [ValidateSet('DVP48ES300R', 'AS228T-A')]
    [string]$Target = 'DVP48ES300R',

    [string]$DriverName = '',

    [int]$ReceiveTimeoutMs = 3000,
    [int]$AckTimeoutMs = 2000
)

$ErrorActionPreference = "Stop"
$targetConfig = @{
    'DVP48ES300R' = @{ driver = 'DVP48ES300R_SIM'; simulator = 'DVP-ES3' }
    'AS228T-A' = @{ driver = 'AS228T_SIM'; simulator = 'AS200' }
}[$Target]
if ([string]::IsNullOrWhiteSpace($DriverName)) { $DriverName = $targetConfig.driver }
$toolVersion = "COMMGR-2.11+$($targetConfig.simulator)-runtime-case-v1"

function ConvertTo-ValueKey([object]$Value) {
    return ConvertTo-Json -InputObject $Value -Compress
}

function Get-JsonProperty([object]$Object, [string]$Name) {
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) {
        throw "JSON object has no property '$Name'"
    }
    return $property.Value
}

function Get-MappedValue([object]$Values, [object]$Value) {
    $key = ConvertTo-ValueKey $Value
    $property = $Values.PSObject.Properties[$key]
    if ($null -eq $property) {
        throw "No DVP selector/comparison bit is allocated for value $key"
    }
    return $property.Value
}

function Add-StepFailure(
    [System.Collections.ArrayList]$Failures,
    [int]$StepIndex,
    [int]$RepeatIndex,
    [string]$OutputName,
    [object]$Expected,
    [object]$Actual
) {
    [void]$Failures.Add([ordered]@{
        step_index = $StepIndex
        repeat_index = $RepeatIndex
        output = $OutputName
        expected = $Expected
        actual = $Actual
    })
}

$result = [ordered]@{
    schema_version = 1
    captured_at = (Get-Date).ToString("o")
    tool_version = $toolVersion
    driver = $DriverName
    target = $Target
    case_id = $CaseId
    status = "inconclusive"
    repetitions_executed = 0
    failures = @()
}

$setup = $null
$comm = $null
try {
    $suite = Get-Content -LiteralPath $SuitePath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($suite.dvp_mapping.target -ne $Target -or $suite.dvp_mapping.commgr_driver -ne $DriverName) {
        throw "suite does not contain the required $Target/$DriverName mapping"
    }
    $case = @($suite.cases | Where-Object { $_.id -eq $CaseId })
    if ($case.Count -ne 1) {
        throw "expected exactly one runtime case named '$CaseId', found $($case.Count)"
    }
    $case = $case[0]
    $mapping = $suite.dvp_mapping

    $sdkRoot = "C:\Program Files (x86)\Delta Industrial Automation\ISPSoft 3.24\DIACommission\DataTracer"
    [Environment]::CurrentDirectory = $sdkRoot
    foreach ($file in (Get-ChildItem -LiteralPath $sdkRoot -Filter "*.dll" -File | Sort-Object Name)) {
        try { [void][Reflection.Assembly]::LoadFrom($file.FullName) } catch {}
    }

    $helper = [DeltaIA.DIAStudio.Communication.Commgr.CommgrHelper]::SharedInstance
    if (-not $helper.IsRunning -or -not $helper.HasDriver($DriverName)) {
        throw "COMMGR or the $DriverName driver is not running"
    }
    $setup = [DeltaIA.DIAStudio.Communication.Setup.Commgr.ModbusCommgrSetup]::CreateWithHelper($helper)
    $data = New-Object "DeltaIA.DIAStudio.Communication.Setup.Commgr.ModbusCommgrSetupData" -ArgumentList 0, $ReceiveTimeoutMs
    $data.DriverName = $DriverName
    $data.StationNumber = 0
    $data.ReceiveTimeout = $ReceiveTimeoutMs
    $setup.SetupData = $data
    if (-not $setup.ValidateSetupData($data) -or -not $setup.Apply()) {
        throw "COMMGR rejected the DVP simulator connection settings"
    }
    $comm = $setup.ModbusComm
    $comm.Connect()
    if (-not $comm.IsConnected) {
        throw "COMMGR did not connect to $DriverName"
    }

    function Set-Coil([int]$Address, [bool]$Value) {
        $exception = [byte]0
        if (-not $comm.TrySetCoil($Address, $Value, [ref]$exception)) {
            throw ("COMMGR coil write failed at 0x{0:X}: exception={1}" -f $Address, $exception)
        }
    }

    function Get-Coil([int]$Address) {
        $buffer = New-Object byte[] 1
        $exception = [byte]0
        if (-not $comm.TryGetCoilStatus($Address, 1, [ref]$buffer, [ref]$exception)) {
            throw ("COMMGR coil read failed at 0x{0:X}: exception={1}" -f $Address, $exception)
        }
        return [bool]$buffer[0]
    }

    # Clear only host-writable harness devices.  Image-identity coils are PLC
    # outputs and must never be overwritten by the test driver.
    $coilBase = [int]$mapping.commgr_coil_base
    $writableLast = if ($null -ne $mapping.writable_last_m) {
        [int]$mapping.writable_last_m
    } else {
        [int]$mapping.last_m
    }
    for ($m = [int]$mapping.first_m; $m -le $writableLast; $m++) {
        Set-Coil ($coilBase + $m) $false
    }

    # Verify a 64-bit digest marker generated from the candidate, task, role,
    # and selected suite.  This makes a completed download observable and
    # prevents a stale simulator image from being scored as the current job.
    if ($null -eq $mapping.image_identity -or @($mapping.image_identity.bits).Count -ne 64) {
        throw "suite does not contain the required 64-bit image identity"
    }
    Start-Sleep -Milliseconds 100
    $identityFailures = New-Object System.Collections.ArrayList
    foreach ($bit in @($mapping.image_identity.bits)) {
        $actual = Get-Coil ([int]$bit.coil_address)
        if ($actual -ne [bool]$bit.expected) {
            [void]$identityFailures.Add([ordered]@{
                bit_index = [int]$bit.bit_index
                expected = [bool]$bit.expected
                actual = $actual
            })
        }
    }
    if ($identityFailures.Count -ne 0) {
        $result.image_identity_failures = @($identityFailures)
        throw "downloaded $Target image identity does not match the submitted job"
    }
    $result.image_identity_sha256 = [string]$mapping.image_identity.sha256

    $failures = New-Object System.Collections.ArrayList
    $stepIndex = 0
    foreach ($step in $case.steps) {
        $repeatCount = [int]$step.repeat
        if ($repeatCount -lt 1) {
            throw "runtime step $stepIndex has an invalid repeat count"
        }
        for ($repeatIndex = 0; $repeatIndex -lt $repeatCount; $repeatIndex++) {
            foreach ($inputProperty in $mapping.inputs.PSObject.Properties) {
                $name = $inputProperty.Name
                $inputMap = $inputProperty.Value
                $value = Get-JsonProperty $step.inputs $name
                if ($inputMap.kind -eq "bool") {
                    if ($value -isnot [bool]) {
                        throw "input '$name' is not Boolean"
                    }
                    Set-Coil ([int]$inputMap.coil_address) ([bool]$value)
                } elseif ($inputMap.kind -eq "selector") {
                    foreach ($selectorProperty in $inputMap.values.PSObject.Properties) {
                        Set-Coil ([int]$selectorProperty.Value.coil_address) $false
                    }
                    $selected = Get-MappedValue $inputMap.values $value
                    Set-Coil ([int]$selected.coil_address) $true
                } else {
                    throw "unsupported input mapping kind '$($inputMap.kind)'"
                }
            }

            $ackAddress = [int]$mapping.step_ack.coil_address
            $requestAddress = [int]$mapping.step_request.coil_address
            $requestValue = -not (Get-Coil $ackAddress)
            Set-Coil $requestAddress $requestValue
            $deadline = (Get-Date).AddMilliseconds($AckTimeoutMs)
            do {
                if ((Get-Coil $ackAddress) -eq $requestValue) { break }
                Start-Sleep -Milliseconds 1
            } while ((Get-Date) -lt $deadline)
            if ((Get-Coil $ackAddress) -ne $requestValue) {
                throw "DVP harness did not acknowledge logical scan $stepIndex/$repeatIndex"
            }
            $result.repetitions_executed += 1

            $shouldCheck = ($step.check -eq "each") -or ($repeatIndex -eq ($repeatCount - 1))
            if ($shouldCheck) {
                foreach ($expectedProperty in $step.expect.PSObject.Properties) {
                    $name = $expectedProperty.Name
                    $expected = $expectedProperty.Value
                    $outputMap = Get-JsonProperty $mapping.outputs $name
                    if ($outputMap.kind -eq "bool") {
                        $actual = Get-Coil ([int]$outputMap.coil_address)
                        if ($actual -ne [bool]$expected) {
                            Add-StepFailure $failures $stepIndex $repeatIndex $name $expected $actual
                        }
                    } elseif ($outputMap.kind -eq "expected_match") {
                        $expectedBit = Get-MappedValue $outputMap.values $expected
                        $matches = Get-Coil ([int]$expectedBit.coil_address)
                        if (-not $matches) {
                            Add-StepFailure $failures $stepIndex $repeatIndex $name $expected "comparison-bit-false"
                        }
                    } elseif ($outputMap.kind -ne "unobserved") {
                        throw "unsupported output mapping kind '$($outputMap.kind)'"
                    }
                }
            }
        }
        $stepIndex += 1
    }

    $result.failures = @($failures)
    $result.status = if ($failures.Count -eq 0) { "pass" } else { "fail" }
    $result.requirement_ids = @($case.requirement_ids)
} catch {
    $result.status = "inconclusive"
    $result.error_type = $_.Exception.GetType().FullName
    $result.error = $_.Exception.Message
} finally {
    if ($null -ne $comm) {
        try { $comm.Disconnect() } catch {}
    }
    if ($null -ne $setup) {
        try { $setup.Dispose() } catch {}
    }
}

$parent = Split-Path -Parent $OutputPath
if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
$result | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $OutputPath -Encoding UTF8
if ($result.status -eq "pass") { exit 0 }
if ($result.status -eq "fail") { exit 2 }
exit 3
