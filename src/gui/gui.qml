import QtQuick 6.8
import QtQuick.Controls 6.8
import QtQuick.Window 6.8

Window {
    id: win
    width: 520
    height: 180
    minimumWidth: 440
    minimumHeight: 150
    maximumWidth: 760
    maximumHeight: 240
    visible: true
    color: "transparent"
    flags: Qt.FramelessWindowHint | Qt.Window
    title: "KAIRO"

    property string uiStatus: "READY"
    property bool busy: false

    readonly property color black: "#000000"
    readonly property color surface: "#0A0A0C"
    readonly property color surface2: "#101012"
    readonly property color border: "#1D1D21"
    readonly property color borderSoft: "#141417"
    readonly property color primary: "#F2F2F2"
    readonly property color muted: "#77777D"
    readonly property color dim: "#3C3C42"
    readonly property color accent: "#D7D7DB"

    function submitTask() {
        var command = commandField.text.trim()
        if (!command || busy)
            return

        busy = true
        uiStatus = "PLANNING"
        kairoBridge.run_task(command)
        commandField.selectAll()
        commandField.forceActiveFocus()
    }

    function statusText() {
        if (uiStatus === "PLANNING") return "Thinking"
        if (uiStatus === "EXECUTING") return "Working"
        if (uiStatus === "COMPLETED") return "Done"
        if (uiStatus === "FAILED") return "Stopped"
        if (uiStatus === "ERROR") return "Something went wrong"
        return "Ready"
    }

    // Subtle animated backdrop: intentionally restrained.
    Rectangle {
        anchors.fill: parent
        radius: 18
        color: black
        border.width: 1
        border.color: border
        clip: true

        Rectangle {
            id: glow
            width: 260
            height: 260
            radius: 130
            x: parent.width - width * 0.38
            y: parent.height - height * 0.70
            color: "#FFFFFF"
            opacity: 0.018

            SequentialAnimation on opacity {
                running: !busy
                loops: Animation.Infinite
                NumberAnimation { to: 0.026; duration: 1800; easing.type: Easing.InOutSine }
                NumberAnimation { to: 0.010; duration: 1800; easing.type: Easing.InOutSine }
            }

            SequentialAnimation on x {
                running: true
                loops: Animation.Infinite
                NumberAnimation { to: parent.width - width * 0.44; duration: 7000; easing.type: Easing.InOutSine }
                NumberAnimation { to: parent.width - width * 0.30; duration: 7000; easing.type: Easing.InOutSine }
            }
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 1
            color: borderSoft
        }
    }

    // Lets the whole window be dragged.
    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton
        z: 0
        onPressed: function(mouse) {
            win.startSystemMove()
        }
    }

    Column {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12
        z: 1

        Row {
            width: parent.width
            height: 28
            spacing: 10

            Rectangle {
                width: 28
                height: 28
                radius: 9
                color: surface2
                border.width: 1
                border.color: border

                Text {
                    anchors.centerIn: parent
                    text: "K"
                    color: primary
                    font.pixelSize: 14
                    font.bold: true
                }
            }

            Column {
                width: parent.width - 110
                spacing: 1
                anchors.verticalCenter: parent.verticalCenter

                Text {
                    text: "KAIRO"
                    color: primary
                    font.pixelSize: 11
                    font.bold: true
                    font.letterSpacing: 1.5
                }

                Row {
                    spacing: 6

                    Rectangle {
                        width: 6
                        height: 6
                        radius: 3
                        anchors.verticalCenter: parent.verticalCenter
                        color: busy ? accent : dim

                        SequentialAnimation on opacity {
                            running: busy
                            loops: Animation.Infinite
                            NumberAnimation { to: 0.25; duration: 650 }
                            NumberAnimation { to: 1.0; duration: 650 }
                        }
                    }

                    Text {
                        text: statusText()
                        color: muted
                        font.pixelSize: 8
                    }
                }
            }

            Item { width: 1; height: 1 }

            Rectangle {
                width: 28
                height: 28
                radius: 9
                color: "transparent"
                border.width: 1
                border.color: border

                Text {
                    anchors.centerIn: parent
                    text: "—"
                    color: muted
                    font.pixelSize: 11
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: win.showMinimized()
                }
            }

            Rectangle {
                width: 28
                height: 28
                radius: 9
                color: "transparent"
                border.width: 1
                border.color: border

                Text {
                    anchors.centerIn: parent
                    text: "×"
                    color: muted
                    font.pixelSize: 13
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: Qt.quit()
                }
            }
        }

        Text {
            width: parent.width
            text: "What should I do?"
            color: primary
            font.pixelSize: 19
            font.weight: Font.Medium
        }

        Row {
            width: parent.width
            height: 48
            spacing: 8

            Rectangle {
                width: parent.width - 56
                height: 48
                radius: 12
                color: surface
                border.width: 1
                border.color: commandField.activeFocus ? "#2A2A2F" : border

                Behavior on border.color {
                    ColorAnimation { duration: 120 }
                }

                TextField {
                    id: commandField
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    anchors.rightMargin: 10
                    anchors.topMargin: 2
                    anchors.bottomMargin: 2
                    placeholderText: "Tell KAIRO what to do..."
                    placeholderTextColor: muted
                    color: primary
                    font.pixelSize: 11
                    selectByMouse: true
                    enabled: !busy
                    background: Item {}
                    Keys.onReturnPressed: submitTask()
                }
            }

            Rectangle {
                width: 48
                height: 48
                radius: 12
                color: busy ? surface : surface2
                border.width: 1
                border.color: busy ? borderSoft : "#28282D"

                Text {
                    anchors.centerIn: parent
                    text: busy ? "…" : "↑"
                    color: busy ? muted : primary
                    font.pixelSize: busy ? 16 : 18
                    font.bold: true
                }

                MouseArea {
                    anchors.fill: parent
                    enabled: !busy
                    onClicked: submitTask()
                }
            }
        }

        Text {
            text: busy ? "KAIRO is working on it…" : "Press Ctrl+K to focus the command box"
            color: dim
            font.pixelSize: 8
        }
    }

    Connections {
        target: kairoBridge

        function onStatus_changed(status) {
            uiStatus = status
            busy = status === "PLANNING" || status === "EXECUTING"
        }
    }

    Shortcut {
        sequence: "Ctrl+K"
        enabled: !busy
        onActivated: commandField.forceActiveFocus()
    }

    Component.onCompleted: commandField.forceActiveFocus()
}
