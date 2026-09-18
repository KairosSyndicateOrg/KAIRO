import QtQuick
import QtQuick.Controls
import QtQuick.Window

Window {
    id: root

    width: 760
    height: 82

    visible: true
    title: "KAIRO"

    color: "transparent"

    flags: Qt.FramelessWindowHint | Qt.Window

    property string appState: "idle"
    property string resultText: ""

    // =========================================================
    // BACKEND CONNECTION
    // =========================================================

    Connections {
        target: kairoBridge

        function onStatus_changed(status) {

            if (status === "PLANNING") {
                root.appState = "working"
                root.resultText = "Gemini is planning..."
            }

            else if (status === "COMPLETED") {
                root.completeTask()
            }

            else if (status === "ERROR") {
                root.appState = "idle"
                root.resultText = "Task failed."
                commandInput.enabled = true
            }
        }
    }


    // =========================================================
    // FUNCTIONS
    // =========================================================

    function startWorking() {

        if (commandInput.text.trim().length === 0)
            return

        appState = "working"
        resultText = ""

        commandInput.enabled = false

        kairoBridge.run_task(
            commandInput.text.trim()
        )
    }


    function completeTask() {

        appState = "completed"
        resultText = "Task completed successfully."

        commandInput.enabled = true
    }


    function resetTask() {

        appState = "idle"
        resultText = ""

        commandInput.enabled = true
        commandInput.text = ""

        commandInput.forceActiveFocus()
    }


    // =========================================================
    // MAIN BACKGROUND
    // =========================================================

    Rectangle {
        id: background

        anchors.fill: parent

        radius: 24

        color: "#080B12"

        border.width: 1
        border.color: root.appState === "working"
                      ? "#3948A0"
                      : "#1B2435"


        // =====================================================
        // SUBTLE GLOW
        // =====================================================

        Rectangle {
            anchors.fill: parent

            anchors.margins: -3

            radius: 27

            color: "transparent"

            border.width: 2

            border.color: root.appState === "working"
                          ? "#5267FF"
                          : "#18213A"

            opacity: root.appState === "working"
                     ? 0.45
                     : 0.18

            Behavior on opacity {
                NumberAnimation {
                    duration: 300
                }
            }
        }


        // =====================================================
        // WINDOW DRAG AREA
        // =====================================================

        MouseArea {
            id: dragArea

            anchors.fill: parent

            acceptedButtons: Qt.LeftButton

            onPressed: {
                root.startSystemMove()
            }
        }


        // =====================================================
        // KAIRO LOGO
        // =====================================================

        Row {
            id: logo

            anchors.left: parent.left
            anchors.leftMargin: 22

            anchors.verticalCenter: parent.verticalCenter

            spacing: 9


            Text {
                text: "✦"

                color: "#687AFF"

                font.pixelSize: 17
            }


            Text {
                text: "KAIRO"

                color: "#EEF1FF"

                font.pixelSize: 13

                font.bold: true

                font.letterSpacing: 2
            }


            Text {
                text: "AI"

                color: "#5366FF"

                font.pixelSize: 9

                font.bold: true

                font.letterSpacing: 1
            }
        }


        // =====================================================
        // STATUS DOT
        // =====================================================

        Rectangle {
            id: statusDot

            width: 7
            height: 7

            radius: 3.5

            anchors.left: logo.right
            anchors.leftMargin: 18

            anchors.verticalCenter: parent.verticalCenter

            color: root.appState === "working"
                   ? "#687AFF"
                   : root.appState === "completed"
                     ? "#66D69A"
                     : "#536174"


            SequentialAnimation on opacity {

                running: root.appState === "working"

                loops: Animation.Infinite

                NumberAnimation {
                    from: 1
                    to: 0.25

                    duration: 600
                }

                NumberAnimation {
                    from: 0.25
                    to: 1

                    duration: 600
                }
            }
        }


        // =====================================================
        // COMMAND INPUT
        // =====================================================

        TextField {
            id: commandInput

            anchors.left: statusDot.right
            anchors.leftMargin: 18

            anchors.verticalCenter: parent.verticalCenter

            width: 480
            height: 52

            placeholderText: root.appState === "working"
                            ? "Kairo is working..."
                            : root.appState === "completed"
                              ? "Task completed"
                              : "What should I do?"

            placeholderTextColor: "#465267"

            color: "#EEF2FF"

            font.pixelSize: 15

            background: null

            enabled: root.appState !== "working"

            selectByMouse: true

            Keys.onReturnPressed: {

                event.accepted = true

                root.startWorking()
            }
        }


        // =====================================================
        // EXECUTE BUTTON
        // =====================================================

        Rectangle {
            id: executeButton

            anchors.right: closeButton.left
            anchors.rightMargin: 10

            anchors.verticalCenter: parent.verticalCenter

            width: 42
            height: 42

            radius: 14

            color: executeArea.containsMouse
                   ? "#687AFF"
                   : "#5267FF"

            scale: executeArea.containsMouse
                   ? 1.06
                   : 1.0

            Behavior on scale {
                NumberAnimation {
                    duration: 130

                    easing.type: Easing.OutBack
                }
            }

            Behavior on color {
                ColorAnimation {
                    duration: 130
                }
            }


            Text {
                anchors.centerIn: parent

                text: root.appState === "working"
                      ? "•••"
                      : "→"

                color: "white"

                font.pixelSize: root.appState === "working"
                               ? 10
                               : 21

                font.bold: true
            }


            MouseArea {
                id: executeArea

                anchors.fill: parent

                hoverEnabled: true

                cursorShape: Qt.PointingHandCursor

                enabled: root.appState !== "working"

                onClicked: {
                    root.startWorking()
                }
            }
        }


        // =====================================================
        // CLOSE BUTTON
        // =====================================================

        Rectangle {
            id: closeButton

            anchors.right: parent.right
            anchors.rightMargin: 13

            anchors.verticalCenter: parent.verticalCenter

            width: 32
            height: 32

            radius: 16

            color: closeArea.containsMouse
                   ? "#25131A"
                   : "transparent"


            Text {
                anchors.centerIn: parent

                text: "×"

                color: closeArea.containsMouse
                       ? "#FF718C"
                       : "#667286"

                font.pixelSize: 18
            }


            MouseArea {
                id: closeArea

                anchors.fill: parent

                hoverEnabled: true

                cursorShape: Qt.PointingHandCursor

                onClicked: {
                    root.close()
                }
            }
        }
    }
}